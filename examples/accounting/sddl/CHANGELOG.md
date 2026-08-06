# SDDL 变更日志

## 2026-08-06 · L2 修订 · define-discrepancy

**变更**：定义差异判定标准（spec_gap 修复）

| 项 | 值 |
|----|-----|
| 变更级别 | L2 增量修订 |
| 触发 | spec_gap：B004 的"不平衡"判定标准未定义，实现时自由解释 |
| spec 版本 | 0.1.0 → 0.1.1 |
| 决策点重确认 | DP-005（新增，confirmed：应收 vs 实收不符） |
| 影响面 | B003/B004/B006 + detectDiscrepancy + LedgerEntry + 3 个测试 |
| SQC | ✅ 通过 |
| 测试 | ✅ 13 passed（修订后） |
| 重新冻结 | ✅ v0.1.1 frozen |
