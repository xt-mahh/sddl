#!/usr/bin/env python3
"""SDDL v2.0 架构检查器（架构 Loop 门禁 + 派生 Loop C-arch 维度）

用法:
    python3 check_arch.py <project_root> [--json] [--verbose]

检查项:
    C-arch-def1 模块↔domain spec 所有权双向覆盖
              - architecture.owns 引用的 domain 在 specs/ 中存在
              - specs/ 中每个 frozen spec 的 domain 恰有一个 owner
              - single_module: true 时 specs 必须恰有 1 个 domain
    C-arch-def2 代码 import 图 = 声明 depends_on（需 --with-imports，派生后才有代码）
    C-arch-def3 模块代码落到声明目录（需 --with-imports）
    C-arch-struct schema 合法（meta/modules/decision_points 必填字段）

注意: C-arch-sem（职责内聚性）由 LLM Checklist 投票裁决，本脚本不做语义判断
      （分工原则：脚本是证据收集器，agent 是裁判，见 llm-review.md）

退出码: 0 = pass, 1 = fail
"""
import argparse
import ast
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("需要 PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ARCH_FIELDS = ["meta", "modules", "decision_points", "directory_layout"]
MODULE_FIELDS = ["name", "responsibilities", "owns", "depends_on", "path"]
DP_FIELDS = ["id", "topic", "default", "category", "requires_confirmation", "status"]
DP_STATUSES = {"pending", "confirmed", "modified", "delegated"}


def collect_issues(root: Path, with_imports: bool):
    issues = []          # fail 项
    warnings = []        # 不阻塞但应修
    facts = {}           # 供 --json 输出的证据

    arch_path = root / "sddl" / "architecture.yaml"
    if not arch_path.exists():
        issues.append({"check": "C-arch-struct", "msg": "缺少 sddl/architecture.yaml"})
        return issues, warnings, facts

    arch = yaml.safe_load(arch_path.read_text(encoding="utf-8"))
    if not isinstance(arch, dict):
        issues.append({"check": "C-arch-struct", "msg": "architecture.yaml 不是合法映射"})
        return issues, warnings, facts

    # ---------- C-arch-struct ----------
    for f in ARCH_FIELDS:
        if f not in arch:
            issues.append({"check": "C-arch-struct", "msg": f"缺少必填字段 {f}"})

    meta = arch.get("meta") or {}
    for f in ["id", "version", "status"]:
        if not meta.get(f):
            issues.append({"check": "C-arch-struct", "msg": f"meta.{f} 缺失或为空"})

    single = bool(arch.get("single_module", False))
    modules = arch.get("modules") or []
    if not single and not modules:
        issues.append({"check": "C-arch-struct",
                       "msg": "modules 为空且未声明 single_module: true"})

    names = [m.get("name") for m in modules if isinstance(m, dict)]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        issues.append({"check": "C-arch-struct", "msg": f"模块名重复: {sorted(dup)}"})

    # C-arch-struct：模块 path 重叠/嵌套禁止（文件归属无判据，def2/def3 会失效）
    # 最长路径前缀归属是常见隐式约定，但依赖声明顺序，这里显式 fail 要求物理隔离
    norm_paths = {}
    for m in modules:
        if not isinstance(m, dict) or not m.get("path"):
            continue
        p = str(m["path"]).rstrip("/")
        for other, op in norm_paths.items():
            if p.startswith(op + "/") or op.startswith(p + "/"):
                issues.append({"check": "C-arch-struct",
                               "msg": f"模块 {m['name']} 与 {other} 的 path 重叠/嵌套: {p} vs {op}"
                                      f"（文件归属无判据；将子模块代码移入独立子目录）"})
        norm_paths[m["name"]] = p
    # single_module 豁免时 path 不参与检查

    for m in modules:
        if not isinstance(m, dict):
            continue
        for f in MODULE_FIELDS:
            if f not in m:
                issues.append({"check": "C-arch-struct",
                               "msg": f"模块 {m.get('name', '?')} 缺少必填字段 {f}"})
        if not (m.get("responsibilities") or []):
            issues.append({"check": "C-arch-struct",
                           "msg": f"模块 {m.get('name', '?')} responsibilities 为空（C-arch-sem 无审点）"})

    for dp in arch.get("decision_points") or []:
        for f in DP_FIELDS:
            if f not in dp:
                issues.append({"check": "C-arch-struct",
                               "msg": f"决策点 {dp.get('id', '?')} 缺少字段 {f}"})
        if dp.get("status") not in DP_STATUSES:
            issues.append({"check": "C-arch-struct",
                           "msg": f"决策点 {dp.get('id', '?')} status 非法: {dp.get('status')}"})
    facts["pending_dps"] = [dp["id"] for dp in (arch.get("decision_points") or [])
                            if dp.get("status") == "pending"]

    # depends_on 合法性：引用存在的模块名 + 无环（floyd 简化版：DFS）
    name_set = set(names)
    for m in modules:
        for dep in m.get("depends_on") or []:
            if dep not in name_set:
                issues.append({"check": "C-arch-def2",
                               "msg": f"模块 {m.get('name')} depends_on 不存在的模块: {dep}"})
            if dep == m.get("name"):
                issues.append({"check": "C-arch-def2",
                               "msg": f"模块 {m.get('name')} 依赖自身"})
    graph = {m["name"]: list(m.get("depends_on") or []) for m in modules if isinstance(m, dict)}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def dfs(n, stack):
        color[n] = GRAY
        for d in graph.get(n, []):
            if color.get(d) == GRAY:
                issues.append({"check": "C-arch-def2",
                               "msg": f"依赖成环: {' -> '.join(stack + [n, d])}"})
            elif color.get(d) == WHITE:
                dfs(d, stack + [n])
        color[n] = BLACK

    for n in graph:
        if color[n] == WHITE:
            dfs(n, [])

    # ---------- C-arch-def1 所有权双向覆盖 ----------
    specs_dir = root / "sddl" / "specs"
    spec_domains = []
    if specs_dir.exists():
        for sp in sorted(specs_dir.glob("*/spec.yaml")):
            try:
                s = yaml.safe_load(sp.read_text(encoding="utf-8"))
                d = (s or {}).get("meta", {}).get("domain")
                if d:
                    spec_domains.append(d)
            except yaml.YAMLError:
                warnings.append(f"specs 解析失败: {sp}")

    owned = {}
    for m in modules:
        for d in m.get("owns") or []:
            owned.setdefault(d, []).append(m.get("name"))

    multi = {d: owners for d, owners in owned.items() if len(owners) > 1}
    if multi:
        issues.append({"check": "C-arch-def1", "msg": f"domain 多 owner: {multi}"})
    orphan = [d for d in owned if d not in spec_domains]
    if orphan:
        issues.append({"check": "C-arch-def1",
                       "msg": f"owns 引用不存在的 domain spec: {orphan}"})
    uncovered = [d for d in spec_domains if d not in owned]
    if uncovered and not single:
        issues.append({"check": "C-arch-def1",
                       "msg": f"domain spec 无 owner 模块: {uncovered}"})
    if single and len(spec_domains) != 1:
        issues.append({"check": "C-arch-def1",
                       "msg": f"single_module: true 但 specs 有 {len(spec_domains)} 个 domain"})
    facts["spec_domains"] = spec_domains
    facts["ownership"] = owned

    # ---------- 并行派生组推导（依赖图拓扑分层，v2.0） ----------
    # 无依赖关系的模块可并行派生；同层模块互不依赖，可安全多 agent 并行
    if modules:
        deps_map = {m["name"]: set(m.get("depends_on") or [])
                    for m in modules if isinstance(m, dict)}
        parallel_groups = []
        remaining = dict(deps_map)
        while remaining:
            ready = sorted(n for n, d in remaining.items() if not (d & set(remaining)))
            if not ready:  # 成环兜底（已在 C-arch-def2 报过）
                break
            parallel_groups.append(ready)
            for n in ready:
                del remaining[n]
        facts["parallel_groups"] = parallel_groups
        facts["max_parallelism"] = max((len(g) for g in parallel_groups), default=0)

    # ---------- C-arch-def2/def3 import 图与目录（派生后） ----------
    if with_imports:
        violations, dir_issues, import_graph = check_imports(root, modules)
        issues += violations + dir_issues
        facts["import_graph"] = import_graph

    return issues, warnings, facts


def module_name_to_pkg(module_name: str) -> str:
    return module_name.replace("-", "_")


def check_imports(root: Path, modules):
    issues = []
    dir_issues = []
    import_graph = {}

    for m in modules:
        mod_path = root / m.get("path", "")
        if not mod_path.exists():
            dir_issues.append({"check": "C-arch-def3",
                               "msg": f"模块 {m['name']} 声明目录不存在: {m.get('path')}"})
            continue
        # 代码文件探测：Python 参考收集器只识别 .py；
        # 目录存在但无 .py 时区分「空目录」与「非 Python 技术栈」——
        # 后者显式降级警告（触发项目收集器构造，见 references/evidence-contract.md），
        # 绝不静默给空 import 图（空证据会让 C-arch-def2 假 pass）
        py_files = sorted(mod_path.rglob("*.py"))
        has_code = any(mod_path.rglob(f"*{ext}") for ext in
                       (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".java"))
        if not py_files:
            if has_code:
                issues.append({"check": "C-arch-def2",
                               "msg": f"模块 {m['name']} 目录为非 Python 技术栈: {m.get('path')} —— "
                                      f"参考收集器不适用，须按 evidence-contract.md 构造项目收集器"
                                      f"（构造后落 sddl/checks/ 并 git 固化，C-arch-def2/def3 由其接管）"})
            else:
                dir_issues.append({"check": "C-arch-def3",
                                   "msg": f"模块 {m['name']} 目录无代码文件: {m.get('path')}"})
            continue
        # 每个 src 顶层包 = 一个模块，import 首段对齐
        deps = set()
        src_root = mod_path.parent
        for pf in py_files:
            try:
                tree = ast.parse(pf.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                issues.append({"check": "C-arch-def2",
                               "msg": f"无法解析: {pf.relative_to(root)}"})
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    segs = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    segs = [node.module.split(".")[0]]
                else:
                    continue
                for seg in segs:
                    deps.add(seg)
        import_graph[m["name"]] = sorted(deps)

    # import 段名 -> 模块名（约定：模块名 kebab → 包名 snake）
    pkg_to_mod = {module_name_to_pkg(m["name"]): m["name"]
                  for m in modules if isinstance(m, dict)}
    for m in modules:
        declared = set(m.get("depends_on") or [])
        actual = {pkg_to_mod[d] for d in import_graph.get(m["name"], []) if d in pkg_to_mod}
        undeclared = actual - declared
        if undeclared:
            issues.append({"check": "C-arch-def2",
                           "msg": f"模块 {m['name']} 越界 import（未声明依赖）: {sorted(undeclared)}"})
    # 幽灵模块检查（C-arch-def3）：src 下的顶层包目录必须都在 modules.path 劙明
    # 否则未声明模块的越界 import 逃过 def2 检查（e2e 实测漏检）
    src_dir = root / "src"
    if src_dir.exists():
        declared_paths = set()
        for m in modules:
            p = str(m.get("path", ""))
            declared_paths.add(Path(p).name)
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and not any(
                    (child / f).exists() for f in ("__init__.py", "__main__.py")):
                # 无 __init__.py 的目录不是包，跳过（资源目录等）
                has_py = any(child.rglob("*.py"))
                if not has_py:
                    continue
            if child.is_dir() and child.name not in declared_paths:
                dir_issues.append({"check": "C-arch-def3",
                                   "msg": f"src/ 下存在未声明模块的代码目录: {child.name}"
                                          f"（architecture.yaml 未登记，越界 import 逃逸）"})
    return issues, dir_issues, import_graph


def main():
    ap = argparse.ArgumentParser(description="SDDL v2.0 architecture checker")
    ap.add_argument("project_root", help="项目根目录（含 sddl/architecture.yaml）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--with-imports", action="store_true",
                    help="启用 C-arch-def2/def3（派生 Loop 有代码后）")
    args = ap.parse_args()

    root = Path(args.project_root)
    issues, warnings, facts = collect_issues(root, args.with_imports)

    ok = not issues
    if args.json:
        print(json.dumps({"pass": ok, "issues": issues, "warnings": warnings,
                          "facts": facts}, ensure_ascii=False, indent=2))
    else:
        for i in issues:
            print(f"[FAIL] {i['check']}: {i['msg']}")
        for w in warnings:
            print(f"[WARN] {w}")
        print("RESULT:", "pass" if ok else "fail")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
