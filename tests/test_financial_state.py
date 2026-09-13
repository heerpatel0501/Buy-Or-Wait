import pytest
from code.state import FinancialStateLayer
from code.models import Request, FinancialProfile
from decimal import Decimal
from datetime import date

def test_financial_state_ignores_pending_credits():
    # BUG 4 verified
    layer = FinancialStateLayer(None)
    profile = FinancialProfile("u1", "USD", Decimal("100"), Decimal("0"), [], [], [], [], [], None)
    req = Request("r1", "u1", date(2026, 9, 13), "purchase", Decimal("50"), None, False, "")
    
    from code.models import FinancialEvent
    events = [
        FinancialEvent("e1", "u1", "transfer", "Salary", "Income", "credit", Decimal("1000"), "USD", date(2026, 9, 14), None, "pending", None, "fixed", None),
        FinancialEvent("e2", "u1", "transfer", "Rent", "Housing", "debit", Decimal("500"), "USD", date(2026, 9, 14), None, "pending", None, "fixed", None)
    ]
    
    state = layer.reconstruct(events, req, profile)
    future_events = state["explicit_future_events"]
    
    assert len(future_events) == 1
    assert future_events[0].event_id == "e2" # e1 is pending credit, should be ignored
    assert future_events[0].direction == "debit"
