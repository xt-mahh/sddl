---
description: "SDDL 决策点确认：摘要 clarify 逐项确认（含自定义输入），产出确认记录"
skills: sddl
---

执行 SDDL **confirm 阶段**（形成/架构 Loop 共用，phase 感知）。

1. 收集当前待确认决策点：spec 草稿的 DP（spec_status 未 frozen）或 architecture.yaml 的架构 DP（arch_status 未 frozen），与用户核对范围。
2. 读 skill 的 `templates/decision-summary.md`，逐个决策点发 clarify：业务选项 ≤3 个，第 4 位固定放"自定义输入（Other）"占位；question 文本提示"其他值请选自定义输入"；开放式决策点用无 choices 的 clarify。
3. 用户自定义值走捕获协议：记录 value+reason → 同步 spec/architecture → 确认记录标 modified。
4. 产出 `sddl/decisions/<domain>-confirmation.yaml`（含 overall: approved 签署位），确保无 pending。
5. 结束时：更新 state.yaml + git commit，报告下一步：spec 确认后 `/sddl:freeze`；架构确认后 `/sddl:freeze`（C-arch 检查 + 冻结架构）。
