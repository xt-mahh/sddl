---
description: "SDDL 归档：变更归档、spec 合并、CHANGELOG 更新"
skills: sddl
---

执行 SDDL **archive 阶段**（收敛后收尾）。

1. 前置：verify 收敛（检查报告落 `sddl/checks/` 且通过）。
2. 按 skill 的 `references/formation-loop.md`（变更管理）归档本轮变更：`changes/<name>/` 提案标记完成，将已交付行为合并回 `sddl/specs/<domain>/spec.yaml`（status: evolved），保持 spec 与代码同步——spec 是单一事实来源，交付后不撒谎。
3. 更新 CHANGELOG（版本、决策点、检查报告索引）。
4. 结束时：更新 state.yaml（current_phase 回到可承接新变更的状态）+ git commit（`chore(sddl): archive <change>`），报告：项目进入增量模式，新功能走 `changes/` 提案 + `/sddl:confirm → /sddl:freeze → /sddl:derive`。
