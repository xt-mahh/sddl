---
description: "SDDL 派生 Loop：C1-C4 + C-arch 分层一致性检查、收敛判定与路由"
skills: sddl
---

执行 SDDL **verify 阶段**（派生 Loop 第 2 步）。

1. 运行确定性检查并落盘 `sddl/checks/c1-c4-<domain>-v1.json`：
   `scripts/check_c1_c4.py . --json`（C1/C2/C4b-def + C3 测试执行）
   `scripts/check_arch.py . --with-imports --json`（C-arch-def2/def3）
2. 读 `references/checker-matrix.md` + `references/llm-review.md` 做 LLM 语义审核（C1-sem/C2-sem/C4a/C4b-sem/C-arch-sem）：checklist 二分 + 投票共识率，不打绝对分；C1-def 必须结构反推（解析测试 AST），不信任标签。
3. 收敛判定：硬条件全过 + 软共识率达标（c1_sem≥0.95 c2_sem≥0.95 c4a≥0.90 c4b_sem≥0.90 c_arch_sem≥0.90）+ must 覆盖 100%。
4. 未收敛按 `references/derivation-loop.md`（阶段 3-5）路由：violation → 重派 artifacts；arch_error → 先归因（spec 根因走 spec_error 上溯，否则独立解冻架构）；spec_error → 解冻回形成 Loop，不绕过质量门禁直接改 spec。
5. 结束时：更新 state.yaml 预算 + git commit；收敛则报告下一步：`/sddl:archive`。
