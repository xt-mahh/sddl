---
description: "SDDL 形成 Loop 第 2 步：生成 L1-L5 spec 草稿并标记决策点"
skills: sddl
---

执行 SDDL **spec 阶段**（形成 Loop 第 2 步）。

1. 前置：`sddl/requirements.md` 存在（否则先 `/sddl:interview`）。
2. 读 skill 的 `references/spec-schema.md`，按 `templates/spec-template.yaml` 生成 `sddl/specs/<domain>/spec.yaml`（L1-L5：能力/接口/数据模型/行为/边界与质量约束）。
3. 每处模糊/多解/有风险的默认选择，登记决策点（DP-xxx：topic/default/alternatives/impact），不静默决定。
4. 自检：运行 `scripts/check_sqc.py sddl/specs/<domain>/spec.yaml --verbose`，SQC-def 骨架通过后再进入下一步。
5. 结束时：更新 state.yaml + git commit，报告下一步：`/sddl:confirm`。
