# 变更提案：定义差异判定标准（spec_gap 修复）

## proposal.md

**意图**：spec B004 的"不平衡"判定标准未定义，实现时可自由解释（当前实现选了"≤0 金额 = 差异"），但这与真实业务"应收 vs 实收不符"不符。需补充差异判定标准。

**范围**：
- 修改 B004 的 GIVEN/THEN（明确差异判定标准）
- 新增决策点 DP-005（差异判定标准）
- 同步修改实现 + 测试

**理由**：spec_gap——实现暴露了 spec 未定义的关键业务规则。

## 变更级别

**L2 增量修订**（改行为语义但兼容：B004 场景细化，不删接口不签名）

## 影响面分析

| 元素 | 受影响 |
|------|--------|
| behavior B004 | detectDiscrepancy 实现 + test_detectDiscrepancy_found + docs |
| behavior B003 | detectDiscrepancy 实现（平衡判定）+ test_detectDiscrepancy_none |
| behavior B006 | settle 的差异检查依赖 detectDiscrepancy |
| data_model DiscrepancyReport | differences 结构可能变化 |
