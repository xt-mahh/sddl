---
description: "SDDL 形成 Loop 第 1 步：分层需求访谈（L0-L2 必答，≤10 问），产出需求陈述"
skills: sddl
---

执行 SDDL **interview 阶段**（形成 Loop 第 1 步）。

1. 先运行 `scripts/sddl_status.py .` 确认当前处于 formation 阶段且未生成 spec。
2. 读 skill 的 `references/formation-loop.md`（阶段 1），按分层结构访谈：L0 目标与非目标、L1 用户与场景、L2 核心行为——必答层问完即止，总数 ≤10 问。
3. 产出需求陈述写入 `sddl/requirements.md`；模糊处不做任何替用户决定，留待 spec 阶段登记决策点。
4. 结束时：更新 state.yaml + git commit，报告下一步：`/sddl:spec`。
