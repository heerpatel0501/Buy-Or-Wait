import pytest
from code.optimizer import Optimizer
from code.models import FinancialProfile, Request
from decimal import Decimal
from datetime import date

def test_optimizer_ranking():
    profile = FinancialProfile("u1", "USD", Decimal("100"), Decimal("20"), [], [], [], [], [], None)
    req = Request("r1", "u1", date(2026, 9, 13), "purchase", Decimal("50"), date(2026, 12, 1), False, "")
    
    candidates = [
        # Plan 1: No spending changes, earlier date
        {"method": "full_payment", "plan": {date(2026, 9, 14): Decimal("50")}, "spending_changes": [], "total_paid": Decimal("50"), "option_id": None},
        # Plan 2: Spending changes needed
        {"method": "full_payment", "plan": {date(2026, 9, 13): Decimal("50")}, "spending_changes": [{"type": "stop", "target_event_id": "e1"}], "total_paid": Decimal("50"), "option_id": None}
    ]
    
    opt = Optimizer(profile, req)
    best = opt.rank_plans(candidates)
    
    assert best["spending_changes"] == [] # Rule 2: Fewer spending changes is preferred
    assert best["plan_string"] == "2026-09-14:50" # BUG 7 format check
