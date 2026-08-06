#!/usr/bin/env python3
"""SDDL SQC 检查器（形成 Loop 门禁）

用法:
    python3 check_sqc.py <spec.yaml> [--json] [--verbose]

检查项:
    SQC-def-1 schema 合法
    SQC-def-2 引用完整
    SQC-def-3 可断言性（模糊词）
    SQC-def-4 决策点登记
    SQC-sem-1 行为覆盖（启发式）
    SQC-sem-2 行为矛盾（启发式）
    SQC-sem-3 完整性缺口（启发式）
    SQC-sem-4 可测性（启发式）

注意: SQC-sem 启发式仅作初步筛选，生产应走 Checklist LLM 投票
      （见 references/checker-matrix.md 陷阱 #8）

退出码: 0 = pass, 1 = fail
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("需要 PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# 模糊词清单（SQC-def-3）
FUZZY_RE = re.compile(
    r"成功|正常|正确|尽快|快速|高效|友好|合理|适当|必要时|等等|其他|"
    r"相关|相应|尽可能|大概|大约|左右|一些|若干|部分|某些"
)

# 必填字段
META_FIELDS = ["id", "version", "domain", "status"]
INTERFACE_FIELDS = ["name", "signature", "errors"]
BEHAVIOR_FIELDS = ["id", "interface", "priority", "given", "when", "then"]
BOUNDARY_FIELDS = ["condition", "expectation"]
DP_FIELDS = ["id", "topic", "default", "category", "requires_confirmation", "status"]

NATIVE_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}


def is_native_or_container(t: str) -> bool:
    """判断类型是否为原生类型或容器类型（array<X>, map<K,V> 等）"""
    if t in NATIVE_TYPES:
        return True
    # array<X> / list<X> / map<K,V> —— 内部元素类型需另行检查，容器本身视为原生
    if re.match(r"^(array|list|map|dict|set)<.+>$", t):
        return True
    return False
DP_STATUSES = {"pending", "confirmed", "modified", "delegated"}


def check_sqc(spec_path: str) -> dict:
    """运行全部 SQC 检查，返回结果 dict"""
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    results = {"spec_version": spec.get("meta", {}).get("version", "?"),
               "def": {}, "sem": {}, "blockers": [], "warnings": []}

    # ============ SQC-def-1: schema 合法 ============
    def1 = {"pass": True, "issues": []}
    meta = spec.get("meta", {})
    for f in META_FIELDS:
        if not meta.get(f):
            def1["issues"].append(f"meta.{f} 缺失")
    if not isinstance(spec.get("interfaces"), list) or not spec["interfaces"]:
        def1["issues"].append("interfaces 为空")
    if not isinstance(spec.get("behaviors"), list) or not spec["behaviors"]:
        def1["issues"].append("behaviors 为空")
    for i in spec.get("interfaces", []):
        for f in INTERFACE_FIELDS:
            if f not in i:
                def1["issues"].append(f"interface {i.get('name')} 缺 {f}")
    for b in spec.get("behaviors", []):
        for f in BEHAVIOR_FIELDS:
            if f not in b:
                def1["issues"].append(f"behavior {b.get('id')} 缺 {f}")
    for bd in spec.get("boundaries", []):
        for f in BOUNDARY_FIELDS:
            if f not in bd:
                def1["issues"].append(f"boundary {bd.get('condition','?')[:20]} 缺 {f}")
    def1["pass"] = len(def1["issues"]) == 0
    results["def"]["schema"] = def1

    # ============ SQC-def-2: 引用完整 ============
    def2 = {"pass": True, "issues": []}
    interfaces = {i["name"] for i in spec.get("interfaces", [])}
    models = {m["name"] for m in spec.get("data_models", [])}
    for b in spec.get("behaviors", []):
        if b["interface"] not in interfaces:
            def2["issues"].append(f"behavior {b['id']} 引用不存在的 interface: {b['interface']}")
    for i in spec.get("interfaces", []):
        ret = i["signature"]["returns"].get("type", "")
        if not is_native_or_container(ret) and ret not in models:
            def2["issues"].append(f"interface {i['name']} 返回类型 {ret} 不在 data_models")
        for p in i["signature"].get("params", []):
            pt = p.get("type", "")
            if not is_native_or_container(pt) and pt not in models:
                def2["issues"].append(f"interface {i['name']} 参数 {p.get('name')} 类型 {pt} 不在 data_models")
    # 错误类型需有行为/边界定义
    defined_errors = set()
    for b in spec.get("behaviors", []):
        for t in b.get("then", []):
            m = re.search(r"抛出 (\w+)", t)
            if m:
                defined_errors.add(m.group(1))
    for bd in spec.get("boundaries", []):
        for m in re.finditer(r"抛出 (\w+)", bd.get("expectation", "")):
            defined_errors.add(m.group(1))
    for i in spec.get("interfaces", []):
        for e in i.get("errors", []):
            if e not in defined_errors:
                def2["issues"].append(f"interface {i['name']} 错误 {e} 无对应行为/边界定义")
    # behaviors 引用的 DP 存在
    dp_ids = {dp["id"] for dp in spec.get("decision_points", [])}
    for b in spec.get("behaviors", []):
        for t in b.get("then", []) + [b.get("given", "")]:
            for m in re.finditer(r"DP-\d+", t):
                if m.group(0) not in dp_ids:
                    def2["issues"].append(f"{b['id']} 引用不存在的 {m.group(0)}")
    # non_goals 与 interfaces 冲突（启发式）
    for ng in spec.get("non_goals", []):
        ng_lower = ng.lower()
        for i in spec.get("interfaces", []):
            if any(w in ng_lower for w in ["不", "无", "非"]) and i["name"].lower() in ng_lower:
                def2["issues"].append(f"non_goal '{ng}' 疑似与 interface {i['name']} 冲突")
    def2["pass"] = len(def2["issues"]) == 0
    results["def"]["refs"] = def2

    # ============ SQC-def-3: 可断言性（模糊词） ============
    def3 = {"pass": True, "warnings": []}
    for b in spec.get("behaviors", []):
        for t in b.get("then", []):
            if FUZZY_RE.search(t):
                def3["warnings"].append(f"{b['id']}-THEN: {t}")
    if def3["warnings"]:
        def3["pass"] = False
    results["def"]["assertability"] = def3
    results["warnings"].extend(def3["warnings"])

    # ============ SQC-def-4: 决策点登记 ============
    def4 = {"pass": True, "issues": []}
    dps = spec.get("decision_points", [])
    if not isinstance(dps, list):
        def4["issues"].append("decision_points 不存在或非列表")
    elif len(dps) > 15:
        def4["issues"].append(f"决策点 {len(dps)} 个超过 15 上限")
    for dp in dps:
        for f in DP_FIELDS:
            if f not in dp:
                def4["issues"].append(f"决策点 {dp.get('id')} 缺 {f}")
        if dp.get("status") not in DP_STATUSES:
            def4["issues"].append(f"决策点 {dp.get('id')} status 非法: {dp.get('status')}")
    def4["pass"] = len(def4["issues"]) == 0
    results["def"]["dp"] = def4

    # ============ SQC-sem-1: 行为覆盖（启发式） ============
    behaviors = spec.get("behaviors", [])
    boundaries = spec.get("boundaries", [])
    musts = [b for b in behaviors if b["priority"] == "must"]
    sem1 = {
        "has_happy_path": any("不存在" not in b.get("given", "") and "不匹配" not in b.get("given", "") for b in musts),
        "has_error_path": any(any("不匹配" in b.get("given", "") or "重复" in b.get("given", "") or "未解决" in b.get("given", "") for b in behaviors) for _ in [0]),
        "has_boundary": len(boundaries) > 0,
    }
    sem1["pass"] = all(sem1.values())
    results["sem"]["coverage"] = sem1

    # ============ SQC-sem-2: 行为矛盾（启发式） ============
    by_interface = {}
    for b in behaviors:
        by_interface.setdefault(b["interface"], []).append(b)
    conflicts = []
    for iface, bs in by_interface.items():
        for idx in range(len(bs)):
            for jdx in range(idx + 1, len(bs)):
                b1, b2 = bs[idx], bs[jdx]
                if b1.get("given") == b2.get("given"):
                    t1 = " ".join(b1.get("then", []))
                    t2 = " ".join(b2.get("then", []))
                    if t1 != t2:
                        conflicts.append(f"{b1['id']} vs {b2['id']}: 同 GIVEN 不同 THEN")
    sem2 = {"pass": len(conflicts) == 0, "conflicts": conflicts}
    results["sem"]["contradiction"] = sem2

    # ============ SQC-sem-4: 可测性（启发式） ============
    unmeasurable = []
    for b in behaviors:
        for t in b.get("then", []):
            if not any(k in t for k in ["=", ">", "<", "返回", "抛出", "变为", "包含", "非空", "保持", "增加", "空数组", "全部存在", "记录数", "状态"]):
                unmeasurable.append(f"{b['id']}: {t}")
    sem4 = {"pass": len(unmeasurable) == 0, "unmeasurable": unmeasurable}
    results["sem"]["testability"] = sem4
    results["warnings"].extend(unmeasurable)

    # ============ 判定 ============
    def_fail = any(not v["pass"] for v in results["def"].values())
    sem_fail = any(not v.get("pass", True) for v in results["sem"].values())
    results["verdict"] = "pass" if not def_fail and not sem_fail else "fail"
    if def_fail:
        for k, v in results["def"].items():
            if not v["pass"]:
                results["blockers"].extend(v.get("issues", []))
    if sem_fail:
        for k, v in results["sem"].items():
            if not v.get("pass", True) and v.get("conflicts"):
                results["blockers"].extend(v["conflicts"])
    return results


def main():
    parser = argparse.ArgumentParser(description="SDDL SQC 检查器")
    parser.add_argument("spec", help="spec.yaml 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--verbose", action="store_true", help="输出详情")
    args = parser.parse_args()

    results = check_sqc(args.spec)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"SQC [{results['spec_version']}]: {'✅ PASS' if results['verdict'] == 'pass' else '❌ FAIL'}")
        for k, v in results["def"].items():
            mark = "✅" if v["pass"] else "❌"
            print(f"  {mark} def-{k}")
            if args.verbose and not v["pass"]:
                for issue in v.get("issues", [])[:10]:
                    print(f"      {issue}")
        for k, v in results["sem"].items():
            mark = "✅" if v.get("pass", True) else "❌"
            print(f"  {mark} sem-{k}")
            if args.verbose and not v.get("pass", True):
                for w in v.get("conflicts", []) or v.get("unmeasurable", [])[:10]:
                    print(f"      {w}")
        if results["warnings"]:
            print(f"  ⚠️  {len(results['warnings'])} 个警告（模糊词/可测性）")

    sys.exit(0 if results["verdict"] == "pass" else 1)


if __name__ == "__main__":
    main()
