import pytest
from code.verifier import Verifier
from code.simulator import Simulator
from code.models import Request, FinancialProfile
from decimal import Decimal
from datetime import date

def test_verifier_payment_totals():
    # BUG 6 verified
    profile = FinancialProfile("u1", "USD", Decimal("100"), Decimal("20"), [], [], [], [], [], None)
    state = {"recurring_expenses": [], "recurring_incomes": [], "explicit_future_events": []}
    sim = Simulator(profile, state)
    req = Request("r1", "u1", date(2026, 9, 13), "purchase", Decimal("50"), date(2026, 12, 1), False, "")
    
    verifier = Verifier(sim, req)
    
    # 1. Total matches (50)
    best_plan = {"method": "full_payment", "plan": {date(2026, 9, 13): Decimal("50")}, "spending_changes": []}
    out_row = {
        "affordability_status": "affordable_now",
        "amount_safe_to_pay": "50",
        "earliest_date_for_full_payment": date(2026, 9, 13).isoformat()
    }
    assert verifier.verify(out_row, best_plan) is True
    
    # 2. Total mismatch (49 instead of 50)
    best_plan = {"method": "full_payment", "plan": {date(2026, 9, 13): Decimal("49")}, "spending_changes": []}
    assert verifier.verify(out_row, best_plan) is False
