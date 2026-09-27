---
description: "SDDL 初始化：建 sddl/ 目录骨架与 state.yaml，读已有代码/需求"
skills: sddl
---

执行 SDDL **init 阶段**（项目初始化）。

1. 按已挂载 sddl skill 的 SKILL.md「目录即状态」章节，创建 `sddl/` 骨架：`specs/ changes/ decisions/ checks/` 目录 + `state.yaml`（阶段指针初始化为 formation）。
2. 若项目已有代码/需求文档：通读并登记现状（供后续反向提取 spec）；全新项目则确认技术栈与目标。
3. 可选：按 `templates/constitution-template.md` 与用户共建 `sddl/constitution.md` 项目宪法。
4. 结束时：运行 `scripts/sddl_status.py .`（Windows 用 `python`，Linux/macOS 用 `python3`）确认骨架可识别，写 state.yaml + git commit（`feat(sddl): init complete`），报告下一步：`/sddl:interview`。
