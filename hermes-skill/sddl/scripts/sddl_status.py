#!/usr/bin/env python3
"""SDDL 状态恢复器（目录即状态）

用法:
    python3 sddl_status.py [project_dir]

扫目录结构判断当前进度，输出恢复建议（对应 /sddl:* 命令）。
无对话记忆也能恢复——进度编码在文件存在性里。

退出码: 0 = 正常
"""
import argparse
import sys
from pathlib import Path

# 各阶段判定规则（目录/文件存在性）
def determine_state(root: Path) -> dict:
    sddl_dir = root / "sddl"
    specs = sddl_dir / "specs"
    decisions = sddl_dir / "decisions"
    checks = sddl_dir / "checks"
    changes = sddl_dir / "changes"

    # 收集 spec 文件
    spec_files = list(specs.glob("*/spec.yaml")) if specs.exists() else []

    state = {
        "initialized": sddl_dir.exists() and (sddl_dir / "state.yaml").exists(),
        "spec_files": [str(p.relative_to(root)) for p in spec_files],
        "has_requirements": (sddl_dir / "requirements.md").exists(),
        "has_decisions": any(decisions.glob("*confirmation*.yaml")) if decisions.exists() else False,
        "has_sqc_check": any(checks.glob("sqc-*.json")) if checks.exists() else False,
        "has_c1c4_check": any(checks.glob("c1-c4-*.json")) if checks.exists() else False,
        "has_src": (root / "src").exists(),
        "has_tests": (root / "tests").exists(),
        "has_docs": (root / "docs").exists(),
        "has_changes": any(changes.iterdir()) if changes.exists() else False,
    }

    # 读取 state.yaml 补充
    state_file = sddl_dir / "state.yaml"
    if state_file.exists():
        for line in state_file.read_text().splitlines():
            if line.startswith("spec_status:"):
                state["spec_status"] = line.split(":", 1)[1].strip()
            elif line.startswith("current_phase:"):
                state["current_phase"] = line.split(":", 1)[1].strip()

    # 判定当前阶段 + 下一步命令
    if not state["initialized"]:
        state["stage"] = "not_initialized"
        state["next_command"] = "/sddl:init"
    elif not state["has_requirements"] and not state["spec_files"]:
        state["stage"] = "interview"
        state["next_command"] = "/sddl:interview"
    elif state["spec_files"] and not state["has_decisions"]:
        state["stage"] = "confirm"
        state["next_command"] = "/sddl:confirm"
    elif state["has_decisions"] and not state["has_sqc_check"]:
        state["stage"] = "freeze"
        state["next_command"] = "/sddl:freeze"
    elif state["has_sqc_check"] and state.get("spec_status") == "frozen" and not state["has_src"]:
        state["stage"] = "derive"
        state["next_command"] = "/sddl:derive"
    elif state["has_src"] and state["has_tests"] and not state["has_c1c4_check"]:
        state["stage"] = "verify"
        state["next_command"] = "/sddl:verify"
    elif state["has_c1c4_check"]:
        state["stage"] = "archive_or_new_change"
        state["next_command"] = "/sddl:archive 或新 changes/ 提案"
    else:
        state["stage"] = "unknown"
        state["next_command"] = "检查 sddl/ 结构"

    return state


def main():
    parser = argparse.ArgumentParser(description="SDDL 状态恢复器")
    parser.add_argument("project_dir", nargs="?", default=".", help="项目目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    root = Path(args.project_dir).resolve()
    if not root.exists():
        print(f"目录不存在: {root}", file=sys.stderr)
        sys.exit(1)

    state = determine_state(root)

    if args.json:
        import json
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(f"=== SDDL 状态 [{root.name}] ===")
        print(f"阶段: {state['stage']}")
        print(f"下一步: {state['next_command']}")
        if state.get("spec_status"):
            print(f"spec_status: {state['spec_status']}")
        if state.get("current_phase"):
            print(f"current_phase: {state['current_phase']}")
        if state["spec_files"]:
            print(f"spec: {', '.join(state['spec_files'])}")
        flags = []
        for k, label in [("has_requirements", "需求"), ("has_decisions", "决策确认"),
                         ("has_sqc_check", "SQC"), ("has_src", "代码"),
                         ("has_tests", "测试"), ("has_docs", "文档"),
                         ("has_c1c4_check", "C1-C4"), ("has_changes", "变更提案")]:
            flags.append(f"{label}:{'✓' if state[k] else '✗'}")
        print("进度: " + " ".join(flags))


if __name__ == "__main__":
    main()
