---
description: "SDDL 轻量缺陷通道：diagnose→fix→verify 三态结论，不动冻结 spec"
skills: sddl
---

执行 SDDL **bugfix 阶段**（轻量缺陷修复通道）。

1. 读 skill 的 `references/bugfix-lane.md`：先归因判定 code-level / spec-level。code-level 缺陷走轻量通道；spec-level（spec 本身错/漏）必须回完整 Loop（解冻 → 修订 → 重冻），不得借 bugfix 通道改 spec。
2. diagnose：最小复现 + 定位到模块（读真实源码签名与生产数据流，不凭记忆猜 API）；产出 `sddl/bugs/<slug>/report.md`。
3. fix：最小修复 + 补回归测试；verify：跑 `scripts/check_c1_c4.py . --json` 确认 must 覆盖不回退。
4. 三态结论：fixed（含证据）/ won't fix（含理由）/ spec-level（转完整变更流程）。
5. 结束时：更新 state.yaml + git commit。
