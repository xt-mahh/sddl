"""对账/结算/预算/报销/登录 服务测试
派生自 spec: accounting-service v0.1.0 (frozen)
每个测试对应一个 behavior（标签仅作索引，C1-def L2 会反推断言）
"""
import pytest
from accounting_service import (
    createReconciliation, detectDiscrepancy, settle,
    createBudget, submitExpense, approveExpense, login,
    DuplicateEntryError, UnresolvedDiscrepancyError, AlreadySettledError,
    ReconciliationNotFoundError, InvalidPeriodError, CustomerNotFoundError,
    InvalidAmountError, ExpenseNotFoundError, AlreadyApprovedError,
    InvalidCredentialsError, AccountLockedError, BudgetExceededError,
    UnauthorizedError, _store,
)
from accounting_service.models import LedgerEntry


@pytest.fixture(autouse=True)
def reset_store():
    """每个测试前重置共享 store（测试隔离）"""
    _store.reconciliations.clear()
    _store.budgets.clear()
    _store.expenses.clear()
    _store.login_failures.clear()
    _store.locked_until.clear()
    _store._seq = 0
    yield


# ============================================================
# B001: createReconciliation valid
# ============================================================
@pytest.mark.behavior("B001")
def test_createReconciliation_valid():
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1"),
               LedgerEntry("e2", "2026-08-02", 200.0, "item2")]
    r = createReconciliation("cust1", "2026-08", entries)
    assert r.status == "draft"
    assert r.total_amount == 300.0
    assert len(r.entries) == 2


# ============================================================
# B002: createReconciliation duplicate entry
# ============================================================
@pytest.mark.behavior("B002")
def test_createReconciliation_duplicate():
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1"),
               LedgerEntry("e1", "2026-08-02", 200.0, "item2")]  # 相同 entry_id
    with pytest.raises(DuplicateEntryError):
        createReconciliation("cust1", "2026-08", entries)
    # 记录数不增加
    from accounting_service import _store
    assert len(_store.reconciliations) == 0


# ============================================================
# B003: detectDiscrepancy no discrepancy
# ============================================================
@pytest.mark.behavior("B003")
def test_detectDiscrepancy_none():
    # 平衡：应收 == 实收
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1", expected_amount=100.0, actual_amount=100.0),
               LedgerEntry("e2", "2026-08-02", 100.0, "item2", expected_amount=100.0, actual_amount=100.0)]
    r = createReconciliation("cust1", "2026-08", entries)
    report = detectDiscrepancy(r.reconciliation_id)
    assert report.has_discrepancy is False
    assert report.differences == []


# ============================================================
# B004: detectDiscrepancy found
# ============================================================
@pytest.mark.behavior("B004")
def test_detectDiscrepancy_found():
    # 差异：应收 100 vs 实收 80
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1", expected_amount=100.0, actual_amount=100.0),
               LedgerEntry("e2", "2026-08-02", 80.0, "item2", expected_amount=100.0, actual_amount=80.0)]
    r = createReconciliation("cust1", "2026-08", entries)
    report = detectDiscrepancy(r.reconciliation_id)
    assert report.has_discrepancy is True
    assert len(report.differences) > 0


# ============================================================
# B005: settle with no discrepancy
# ============================================================
@pytest.mark.behavior("B005")
def test_settle_no_discrepancy():
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1"),
               LedgerEntry("e2", "2026-08-02", 100.0, "item2")]
    r = createReconciliation("cust1", "2026-08", entries)
    result = settle(r.reconciliation_id, "admin1")
    assert result.settled_by == "admin1"
    assert r.status == "settled"


# ============================================================
# B006: settle with unresolved discrepancy
# ============================================================
@pytest.mark.behavior("B006")
def test_settle_unresolved_discrepancy():
    # 应收 100 vs 实收 80 → 差异 → 不能结算
    entries = [LedgerEntry("e1", "2026-08-01", 100.0, "item1", expected_amount=100.0, actual_amount=100.0),
               LedgerEntry("e2", "2026-08-02", 80.0, "item2", expected_amount=100.0, actual_amount=80.0)]
    r = createReconciliation("cust1", "2026-08", entries)
    with pytest.raises(UnresolvedDiscrepancyError):
        settle(r.reconciliation_id, "admin1")
    assert r.status == "draft"


# ============================================================
# B007: createBudget valid
# ============================================================
@pytest.mark.behavior("B007")
def test_createBudget_valid():
    b = createBudget("cust1", "2026-08", 5000.0)
    assert b.used_amount == 0
    assert b.amount == 5000.0


# ============================================================
# B008: submitExpense within budget
# ============================================================
@pytest.mark.behavior("B008")
def test_submitExpense_within_budget():
    b = createBudget("cust1", "2026-08", 5000.0)
    e = submitExpense("cust1", 1000.0, "travel", "出差")
    assert e.status == "pending"
    assert b.used_amount == 1000.0


# ============================================================
# B009: submitExpense exceeds budget
# ============================================================
@pytest.mark.behavior("B009")
def test_submitExpense_exceeds_budget():
    b = createBudget("cust1", "2026-08", 5000.0)
    with pytest.raises(BudgetExceededError):
        submitExpense("cust1", 6000.0, "travel", "超预算")
    from accounting_service import _store
    assert len(_store.expenses) == 0


# ============================================================
# B010: approveExpense admin approves
# ============================================================
@pytest.mark.behavior("B010")
def test_approveExpense_admin():
    createBudget("cust1", "2026-08", 5000.0)
    e = submitExpense("cust1", 1000.0, "travel", "出差")
    approved = approveExpense(e.expense_id, "admin1")
    assert approved.status == "approved"


# ============================================================
# B011: approveExpense non-admin
# ============================================================
@pytest.mark.behavior("B011")
def test_approveExpense_non_admin():
    createBudget("cust1", "2026-08", 5000.0)
    e = submitExpense("cust1", 1000.0, "travel", "出差")
    with pytest.raises(UnauthorizedError):
        approveExpense(e.expense_id, "user1")
    assert e.status == "pending"


# ============================================================
# B012: login valid
# ============================================================
@pytest.mark.behavior("B012")
def test_login_valid():
    auth = login("admin1", "secret123")
    assert auth.role == "admin"
    assert auth.token != ""


# ============================================================
# B013: login invalid
# ============================================================
@pytest.mark.behavior("B013")
def test_login_invalid():
    with pytest.raises(InvalidCredentialsError):
        login("admin1", "wrongpass")
