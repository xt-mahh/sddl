---
status: current
spec_version: "0.1.0"
---

# 记账/对账服务 API 文档

> 本文档描述**已实现**能力（与 code 一致，C4b-def 检查）。
> 规划中的能力见 `docs/planned/`。

## 接口总览

| 接口 | 说明 | 错误 |
|------|------|------|
| `createReconciliation` | 创建对账（period 格式 YYYY-MM，entries 非空，无重复 entry_id） | InvalidPeriodError, DuplicateEntryError, CustomerNotFoundError |
| `detectDiscrepancy` | 检测对账差异（0 金额/负数条目视为差异） | ReconciliationNotFoundError |
| `settle` | 结算对账（须无未解决差异，不可重复结算） | ReconciliationNotFoundError, UnresolvedDiscrepancyError, AlreadySettledError |
| `createBudget` | 创建预算（月度周期，amount > 0） | InvalidPeriodError, InvalidAmountError, CustomerNotFoundError |
| `submitExpense` | 提交报销（须在预算内，超预算拒绝） | InvalidAmountError, BudgetExceededError, CustomerNotFoundError |
| `approveExpense` | 审批报销（仅 admin，不可重复审批） | ExpenseNotFoundError, UnauthorizedError, AlreadyApprovedError |
| `login` | 登录（连续 5 次失败锁定 300 秒） | InvalidCredentialsError, AccountLockedError |

## 数据模型

- `LedgerEntry`: entry_id / date / amount / description
- `Reconciliation`: reconciliation_id / customer_id / period / entries / total_amount / status (draft|discrepancy|settled)
- `DiscrepancyReport`: reconciliation_id / has_discrepancy / differences / summary
- `SettlementResult`: reconciliation_id / settled_at / settled_by
- `Budget`: budget_id / customer_id / period / amount / used_amount
- `Expense`: expense_id / customer_id / amount / category / description / status (pending|approved|rejected)
- `AuthResult`: user_id / role (admin|user) / token

## 行为约定

- **对账**：`createReconciliation` 计算 total_amount = entries 金额合计；重复 entry_id 拒绝。
- **差异检测**：entries 含 ≤0 金额视为差异；`detectDiscrepancy` 是纯查询，不修改状态。
- **结算**：仅 `status=draft` 且无差异可结算；结算后 status=settled，不可重复。
- **预算**：月度周期（YYYY-MM）；`submitExpense` 检查预算剩余，超预算抛 BudgetExceededError。
- **报销审批**：仅 admin 角色可审批；pending → approved。
- **登录**：5 次失败锁定 300 秒；密码不明文存储（内存哈希模拟）。

## 安全

- 密码不以明文存储或记录到日志（本实现内存存储，生产需哈希）
- 租户隔离：数据带 tenant_id 字段（当前默认 "default"），生产按 tenant 过滤
- settle 操作记录 audit log（操作人、时间、reconciliation_id）

## 性能

- `detectDiscrepancy` P99 < 800ms（当前内存实现远低于阈值；需环境验证）
