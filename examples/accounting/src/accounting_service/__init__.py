"""记账/对账服务实现
派生自 spec: accounting-service v0.1.0 (frozen)

决策点落实：
- DP-001: 手动标记结算状态（settle 即手动确认）
- DP-002: 预算周期月度（period 格式 YYYY-MM）
- DP-003: 单级审批（管理员 approveExpense）
- DP-004: 共享库 + tenant_id 隔离（本实现用内存 store + tenant 字段）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ============================================================
# 错误类型（spec L1 errors 枚举）
# ============================================================
class DomainError(Exception):
    pass


class InvalidPeriodError(DomainError):
    pass


class DuplicateEntryError(DomainError):
    pass


class CustomerNotFoundError(DomainError):
    pass


class ReconciliationNotFoundError(DomainError):
    pass


class UnresolvedDiscrepancyError(DomainError):
    pass


class AlreadySettledError(DomainError):
    pass


class InvalidAmountError(DomainError):
    pass


class BudgetExceededError(DomainError):
    pass


class ExpenseNotFoundError(DomainError):
    pass


class AlreadyApprovedError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class AccountLockedError(DomainError):
    pass


# ============================================================
# 数据模型（spec L2）
# ============================================================
@dataclass
class LedgerEntry:
    entry_id: str
    date: str
    amount: float
    description: str = ""
    expected_amount: Optional[float] = None   # 应收金额（DP-005: 差异 = 应收 vs 实收不符）
    actual_amount: Optional[float] = None     # 实收金额


@dataclass
class Reconciliation:
    reconciliation_id: str
    customer_id: str
    period: str
    entries: List[LedgerEntry]
    total_amount: float
    status: str = "draft"  # draft | discrepancy | settled
    tenant_id: str = "default"


@dataclass
class DiscrepancyReport:
    reconciliation_id: str
    has_discrepancy: bool
    differences: List[dict] = field(default_factory=list)
    summary: str = ""


@dataclass
class SettlementResult:
    reconciliation_id: str
    settled_at: str
    settled_by: str


@dataclass
class Budget:
    budget_id: str
    customer_id: str
    period: str
    amount: float
    used_amount: float = 0.0
    tenant_id: str = "default"


@dataclass
class Expense:
    expense_id: str
    customer_id: str
    amount: float
    category: str
    description: str = ""
    status: str = "pending"  # pending | approved | rejected
    tenant_id: str = "default"


@dataclass
class AuthResult:
    user_id: str
    role: str  # admin | user
    token: str


# ============================================================
# 存储（内存实现，DP-004: 共享库 + tenant_id 字段隔离）
# ============================================================
class _Store:
    def __init__(self):
        self.reconciliations: Dict[str, Reconciliation] = {}
        self.budgets: Dict[str, Budget] = {}
        self.expenses: Dict[str, Expense] = {}
        self.users: Dict[str, dict] = {
            "admin1": {"password": "CHANGE_ME_PASSWORD", "role": "admin"},
            "user1": {"password": "CHANGE_ME_PASSWORD", "role": "user"},
        }
        self.login_failures: Dict[str, int] = {}
        self.locked_until: Dict[str, datetime] = {}
        self._seq = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"


_store = _Store()


# ============================================================
# 工具函数
# ============================================================
def _validate_period(period: str) -> None:
    """period 格式必须 YYYY-MM（DP-002 月度）"""
    if not (len(period) == 7 and period[4] == "-" and period[:4].isdigit() and period[5:].isdigit()):
        raise InvalidPeriodError(f"period 格式非法: {period}, 需要 YYYY-MM")


def _validate_amount(amount: float) -> None:
    if amount <= 0:
        raise InvalidAmountError(f"amount 必须 > 0, got {amount}")


def _check_customer(customer_id: str) -> None:
    # 简化：customer 存在性检查（真实系统查用户表）
    if customer_id not in {"cust1", "cust2", "cust3"}:
        raise CustomerNotFoundError(f"customer {customer_id} 不存在")


# ============================================================
# L1 接口实现
# ============================================================
def createReconciliation(customer_id: str, period: str, entries: List[LedgerEntry]) -> Reconciliation:
    _validate_period(period)
    _check_customer(customer_id)
    if not entries:
        raise ValueError("entries 不能为空")

    # 查重（B002: 相同 entry_id → DuplicateEntryError）
    seen = set()
    for e in entries:
        if e.entry_id in seen:
            raise DuplicateEntryError(f"重复 entry_id: {e.entry_id}")
        seen.add(e.entry_id)

    total = sum(e.amount for e in entries)
    r = Reconciliation(
        reconciliation_id=_store._next_id("rec"),
        customer_id=customer_id,
        period=period,
        entries=entries,
        total_amount=total,
        status="draft",
        tenant_id="default",
    )
    _store.reconciliations[r.reconciliation_id] = r
    return r


def detectDiscrepancy(reconciliation_id: str) -> DiscrepancyReport:
    r = _store.reconciliations.get(reconciliation_id)
    if r is None:
        raise ReconciliationNotFoundError(f"reconciliation {reconciliation_id} 不存在")

    # 差异检测（DP-005: 差异 = 应收 vs 实收不符）
    # 每笔 entry 若 expected_amount 与 actual_amount 均存在且不等 → 差异
    has_discrepancy = False
    differences = []
    for e in r.entries:
        if e.expected_amount is not None and e.actual_amount is not None:
            if abs(e.expected_amount - e.actual_amount) > 0.001:
                has_discrepancy = True
                differences.append({
                    "entry_id": e.entry_id,
                    "reason": f"应收 {e.expected_amount} vs 实收 {e.actual_amount}",
                })
        elif e.expected_amount is not None and e.actual_amount is None:
            has_discrepancy = True
            differences.append({
                "entry_id": e.entry_id,
                "reason": "缺少实收金额",
            })

    if has_discrepancy:
        # 不修改 r.status —— detectDiscrepancy 是纯查询（spec B003/B004 只要求返回报告）
        pass

    return DiscrepancyReport(
        reconciliation_id=reconciliation_id,
        has_discrepancy=has_discrepancy,
        differences=differences,
        summary=f"{len(differences)} 条差异" if has_discrepancy else "balanced",
    )


def settle(reconciliation_id: str, settled_by: str) -> SettlementResult:
    r = _store.reconciliations.get(reconciliation_id)
    if r is None:
        raise ReconciliationNotFoundError(f"reconciliation {reconciliation_id} 不存在")

    # 检查差异
    report = detectDiscrepancy(reconciliation_id)
    if report.has_discrepancy:
        raise UnresolvedDiscrepancyError("存在未解决差异，不能结算")

    # 重复结算检查（boundary）
    if r.status == "settled":
        raise AlreadySettledError(f"reconciliation {reconciliation_id} 已结算")

    r.status = "settled"
    return SettlementResult(
        reconciliation_id=reconciliation_id,
        settled_at=datetime.utcnow().isoformat(),
        settled_by=settled_by,
    )


def createBudget(customer_id: str, period: str, amount: float) -> Budget:
    _validate_period(period)
    _check_customer(customer_id)
    _validate_amount(amount)
    b = Budget(
        budget_id=_store._next_id("budget"),
        customer_id=customer_id,
        period=period,
        amount=amount,
        used_amount=0.0,
        tenant_id="default",
    )
    _store.budgets[b.budget_id] = b
    return b


def submitExpense(customer_id: str, amount: float, category: str, description: str = "") -> Expense:
    _check_customer(customer_id)
    _validate_amount(amount)

    # 预算检查（B009: 超预算 → BudgetExceededError）
    for b in _store.budgets.values():
        if b.customer_id == customer_id and b.period == _current_month() and b.amount > 0:
            if b.used_amount + amount > b.amount:
                raise BudgetExceededError(f"超预算: used={b.used_amount}, amount={amount}, budget={b.amount}")
            b.used_amount += amount
            break

    e = Expense(
        expense_id=_store._next_id("exp"),
        customer_id=customer_id,
        amount=amount,
        category=category,
        description=description,
        status="pending",
        tenant_id="default",
    )
    _store.expenses[e.expense_id] = e
    return e


def approveExpense(expense_id: str, approver: str) -> Expense:
    e = _store.expenses.get(expense_id)
    if e is None:
        raise ExpenseNotFoundError(f"expense {expense_id} 不存在")

    # 权限检查（B011: 非 admin → UnauthorizedError）
    user = _store.users.get(approver)
    if user is None or user["role"] != "admin":
        raise UnauthorizedError(f"{approver} 无审批权限")

    # 重复审批检查（boundary）
    if e.status == "approved":
        raise AlreadyApprovedError(f"expense {expense_id} 已审批")

    e.status = "approved"
    return e


def login(username: str, password: str) -> AuthResult:
    # 锁定检查（boundary: 连续 5 次失败锁 300 秒）
    if username in _store.locked_until:
        if datetime.utcnow() < _store.locked_until[username]:
            raise AccountLockedError(f"{username} 已锁定")

    user = _store.users.get(username)
    if user is None or user["password"] != password:
        # 记录失败
        _store.login_failures[username] = _store.login_failures.get(username, 0) + 1
        if _store.login_failures[username] >= 5:
            from datetime import timedelta
            _store.locked_until[username] = datetime.utcnow() + timedelta(seconds=300)
        raise InvalidCredentialsError("用户名或密码错误")

    _store.login_failures.pop(username, None)
    _store.locked_until.pop(username, None)
    return AuthResult(
        user_id=username,
        role=user["role"],
        token=f"token-{username}-{datetime.utcnow().timestamp()}",
    )


def _current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")
