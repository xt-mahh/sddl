---
description: "SDDL 架构 Loop：读冻结 specs 划分模块，生成 architecture.yaml（contract 级 DP 附调研）"
skills: sddl
---

执行 SDDL **arch 阶段**（架构 Loop 第 1 步）。

1. 硬前置：`spec_status: frozen`（未冻结先回形成 Loop）。
2. 读 skill 的 `references/architecture-loop.md` + `templates/architecture-template.yaml`，按职责内聚从冻结 specs 划分模块：name/responsibilities/owns/depends_on/path，登记技术栈与目录布局。
3. 决策点与 spec 共用编号池；contract 级 DP（接口契约/存储/框架选型）须 ≥3 候选并附调研笔记——按 `references/research-notes.md` 产出 `sddl/research/<topic>.md`。
4. 自检：运行 `scripts/check_arch.py . --verbose`（struct + def1），通过后进入决策点确认。
5. 结束时：更新 state.yaml + git commit，报告下一步：`/sddl:confirm`（架构决策点）。
