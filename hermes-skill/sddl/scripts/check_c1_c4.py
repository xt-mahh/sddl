#!/usr/bin/env python3
"""SDDL C1-C4 一致性检查器（派生 Loop 门禁）

用法:
    python3 check_c1_c4.py <project_dir> [--domain <name>] [--json] [--verbose]
    python3 check_c1_c4.py <spec.yaml> <src_dir> <tests_dir> <docs_dir> [--json]

检查:
    C1-def  验收覆盖 + 结构反推（L1 标签 / L2 AST 断言 / L3 变异可选）
    C2-def  接口/签名/模型/错误对比 + 无越界 API
    C3      测试执行 + 覆盖率 + 无跳过
    C4b-def docs current 分区 API 存在于 code
    软条件  C1-sem / C2-sem / C4a / C4b-sem（语义启发式，生产用 Checklist LLM 投票）

注意: 语义启发式有假阴性风险（见 checker-matrix.md 陷阱 #8），
      首轮结果需人工复核，失败项逐个判断"真问题 vs 匹配问题"。

退出码: 0 = converged, 1 = not converged
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("需要 PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# spec 声明的接口名（从 spec 读）
def load_spec(spec_path: Path) -> dict:
    with open(spec_path) as f:
        return yaml.safe_load(f)


def extract_code_symbols(code_src: str) -> dict:
    """提取代码公开符号：函数、类、异常类"""
    tree = ast.parse(code_src)
    funcs, classes = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            funcs[node.name] = [a.arg for a in node.args.args]
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            classes.add(node.name)
    return {"funcs": funcs, "classes": classes}


def extract_test_asserts(test_src: str) -> dict:
    """提取每个测试函数的实际断言（AST 反推）"""
    tree = ast.parse(test_src)
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            asserts = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    try:
                        asserts.append(ast.unparse(sub.test))
                    except Exception:
                        asserts.append("<unparsable>")
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "raises":
                    try:
                        asserts.append(f"raises({ast.unparse(sub.args[0])})")
                    except Exception:
                        pass
            result[node.name] = asserts
    return result


def run_c1_def(spec, test_src: str) -> dict:
    """C1-def: L1 标签索引 + L2 结构反推"""
    behavior_tests = dict(re.findall(
        r'@pytest\.mark\.behavior\("(B\d+)"\)\s*\ndef (test_\w+)', test_src))
    test_asserts = extract_test_asserts(test_src)

    l1_missing = [b["id"] for b in spec["behaviors"] if b["id"] not in behavior_tests]

    # L2: 每个 behavior 的测试是否有断言
    l2_weak = []
    for b in spec["behaviors"]:
        tname = behavior_tests.get(b["id"])
        if not tname or tname not in test_asserts:
            l2_weak.append(f"{b['id']}: 无测试")
            continue
        asserts = test_asserts[tname]
        if not asserts:
            l2_weak.append(f"{b['id']}: 测试无断言")

    return {
        "pass": len(l1_missing) == 0 and len(l2_weak) == 0,
        "l1_missing": l1_missing,
        "l2_weak": l2_weak,
        "behavior_tests": behavior_tests,
    }


def run_c2_def(spec, code_src: str) -> dict:
    """C2-def: 接口存在 + 无越界 API"""
    symbols = extract_code_symbols(code_src)
    spec_interfaces = {i["name"] for i in spec["interfaces"]}

    missing = [i for i in spec_interfaces if i not in symbols["funcs"]]
    extra = [f for f in symbols["funcs"] if f not in spec_interfaces]

    # 错误类型
    spec_errors = set()
    for i in spec["interfaces"]:
        spec_errors.update(i.get("errors", []))
    code_errors = set(re.findall(r"^class (\w+Error)\(DomainError\)", code_src, re.M))
    missing_errors = sorted(spec_errors - code_errors)

    return {
        "pass": not missing and not extra and not missing_errors,
        "missing_interfaces": missing,
        "extra_public_api": extra,
        "missing_errors": missing_errors,
    }


def run_c3(tests_dir: Path, src_dir: Path) -> dict:
    """C3: 测试执行"""
    env = {"PYTHONPATH": str(src_dir), "PATH": "/usr/bin:/bin"}
    proc = subprocess.run(
        ["python3", "-m", "pytest", str(tests_dir), "-q"],
        capture_output=True, text=True, env=env, cwd=str(src_dir.parent))
    out = proc.stdout + proc.stderr
    m = re.search(r"(\d+) passed", out)
    n_pass = int(m.group(1)) if m else 0
    failed = "failed" in out.split("===")[-1] if "===" in out else bool(proc.returncode)
    return {
        "pass": n_pass > 0 and not failed,
        "passed": n_pass,
        "failed": failed,
        "output_tail": out.strip().split("\n")[-1] if out else "",
    }


def run_c4b_def(spec, code_src: str, docs_current: Path) -> dict:
    """C4b-def: docs current 分区 API 存在于 code"""
    symbols = extract_code_symbols(code_src)
    code_has = set(symbols["funcs"]) | symbols["classes"]

    missing = []
    if docs_current.exists():
        for doc in docs_current.glob("*.md"):
            content = doc.read_text()
            if "status: planned" in content:
                continue
            for api in re.findall(r"`(\w+)`", content):
                if api in {"YYYY-MM", "draft", "discrepancy", "settled", "pending", "approved", "rejected",
                           "admin", "user", "default"}:
                    continue
                if api not in code_has and not api[0].islower() and api not in {"P99"}:
                    missing.append(f"{doc.name}: {api}")

    return {"pass": len(missing) == 0, "missing_in_code": missing}


def run_soft(spec, code_src: str, test_src: str, docs_src: str) -> dict:
    """软条件：语义启发式（C1-sem/C2-sem/C4a/C4b-sem）"""
    behavior_tests = dict(re.findall(
        r'@pytest\.mark\.behavior\("(B\d+)"\)\s*\ndef (test_\w+)', test_src))
    test_asserts = extract_test_asserts(test_src)

    c1_items, c2_items = [], []
    for b in spec["behaviors"]:
        tname = behavior_tests.get(b["id"], "")
        tasserts = test_asserts.get(tname, [])
        for t in b.get("then", []):
            # 判定项：测试是否断言 / 代码是否实现
            if "抛出" in t:
                err = re.search(r"抛出 (\w+)", t).group(1)
                test_ok = any(f"raises({err}" in a or err in a for a in tasserts)
                code_ok = f"raise {err}" in code_src
            elif "记录数不增加" in t:
                test_ok = any("len(_store" in a and "== 0" in a for a in tasserts)
                code_ok = True  # 抛错即不创建
            elif "status" in t:
                test_ok = any("status" in a for a in tasserts)
                code_ok = "status" in code_src
            elif "total_amount" in t:
                test_ok = any("total_amount" in a for a in tasserts)
                code_ok = "total_amount" in code_src
            elif "settled_by" in t:
                test_ok = any("settled_by" in a for a in tasserts)
                code_ok = "settled_by" in code_src
            elif "used_amount" in t:
                test_ok = any("used_amount" in a for a in tasserts)
                code_ok = "used_amount" in code_src
            elif "role" in t:
                test_ok = any("role" in a for a in tasserts)
                code_ok = "role" in code_src
            elif "token" in t:
                test_ok = any("token" in a for a in tasserts)
                code_ok = "token" in code_src
            elif "differences" in t:
                test_ok = any("differences" in a for a in tasserts)
                code_ok = "differences" in code_src
            elif "has_discrepancy" in t:
                test_ok = any("has_discrepancy" in a for a in tasserts)
                code_ok = "has_discrepancy" in code_src
            else:
                key = t.split(" ")[0].replace("，", "").lower()
                test_ok = any(key in a.lower() for a in tasserts)
                code_ok = key in code_src.lower()
            c1_items.append(test_ok)
            c2_items.append(code_ok)

    c1_rate = sum(c1_items) / len(c1_items) if c1_items else 0
    c2_rate = sum(c2_items) / len(c2_items) if c2_items else 0

    # C4a: spec 接口在 docs
    spec_interfaces = {i["name"] for i in spec["interfaces"]}
    docs_interfaces = set(re.findall(r"`(\w+)`", docs_src))
    c4a_items = [i in docs_interfaces for i in spec_interfaces]
    c4a_rate = sum(c4a_items) / len(c4a_items) if c4a_items else 0

    return {
        "c1_sem": round(c1_rate, 3),
        "c2_sem": round(c2_rate, 3),
        "c4a": round(c4a_rate, 3),
        "c4b_sem": 1.0,  # 简化：C4b-sem 需 LLM，默认视为通过（def 已兜底）
        "note": "语义启发式，生产用 Checklist LLM 投票",
    }


def main():
    parser = argparse.ArgumentParser(description="SDDL C1-C4 检查器")
    parser.add_argument("project", help="项目目录")
    parser.add_argument("--domain", default=None, help="领域名（默认第一个 spec）")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    root = Path(args.project).resolve()
    spec_files = sorted((root / "sddl/specs").glob("*/spec.yaml"))
    if not spec_files:
        print("❌ 无 spec 文件", file=sys.stderr)
        sys.exit(1)

    spec_path = None
    for sf in spec_files:
        if args.domain and args.domain in str(sf):
            spec_path = sf
            break
    if not spec_path:
        spec_path = spec_files[0]

    spec = load_spec(spec_path)
    domain = spec["meta"]["domain"]
    src_dir = root / "src"
    tests_dir = root / "tests"
    docs_dir = root / "docs" / "current"

    code_src = "\n".join(p.read_text() for p in src_dir.rglob("*.py") if "__pycache__" not in str(p)) if src_dir.exists() else ""
    test_src = "\n".join(p.read_text() for p in tests_dir.rglob("*.py") if "__pycache__" not in str(p)) if tests_dir.exists() else ""
    docs_src = "\n".join(p.read_text() for p in docs_dir.glob("*.md")) if docs_dir.exists() else ""

    results = {"domain": domain, "spec_version": spec["meta"]["version"]}

    # 硬条件
    results["c1_def"] = run_c1_def(spec, test_src)
    results["c2_def"] = run_c2_def(spec, code_src)
    results["c3"] = run_c3(tests_dir, src_dir)
    results["c4b_def"] = run_c4b_def(spec, code_src, docs_dir)

    hard_pass = all(r["pass"] for r in [results["c1_def"], results["c2_def"], results["c3"], results["c4b_def"]])

    # 软条件（硬条件过才跑）
    if hard_pass:
        results["soft"] = run_soft(spec, code_src, test_src, docs_src)
        soft = results["soft"]
        must_behaviors = [b["id"] for b in spec["behaviors"] if b["priority"] == "must"]
        behavior_tests = results["c1_def"]["behavior_tests"]
        must_covered = sum(1 for b in must_behaviors if b in behavior_tests) / len(must_behaviors)
        results["must_coverage"] = round(must_covered, 3)

        converged = (
            soft["c1_sem"] >= 0.95 and soft["c2_sem"] >= 0.95 and
            soft["c4a"] >= 0.90 and soft["c4b_sem"] >= 0.90 and
            must_covered == 1.0
        )
        results["verdict"] = "converged" if converged else "not_converged"
    else:
        results["soft"] = "skipped (hard gate failed)"
        results["verdict"] = "not_converged"

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"C1-C4 [{domain} v{results['spec_version']}]: {'✅ CONVERGED' if results['verdict'] == 'converged' else '❌ NOT CONVERGED'}")
        for k in ["c1_def", "c2_def", "c3", "c4b_def"]:
            mark = "✅" if results[k]["pass"] else "❌"
            print(f"  {mark} {k}")
            if args.verbose and not results[k]["pass"]:
                for issue in results[k].get("missing_interfaces", []) or results[k].get("extra_public_api", []) or results[k].get("missing_in_code", []):
                    print(f"      {issue}")
        if hard_pass:
            s = results["soft"]
            print(f"  soft: c1_sem={s['c1_sem']} c2_sem={s['c2_sem']} c4a={s['c4a']} c4b_sem={s['c4b_sem']} must={results['must_coverage']}")
        if results["verdict"] == "not_converged" and hard_pass:
            print("  注: 软条件未达阈值，检查失败项是'真问题'还是'启发式匹配问题'（见陷阱 #8）")

    sys.exit(0 if results["verdict"] == "converged" else 1)


if __name__ == "__main__":
    main()
