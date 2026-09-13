import pytest
from code.solver import Solver
from code.simulator import Simulator
from code.models import Request, FinancialProfile, PaymentOption
from decimal import Decimal
from datetime import date

def test_solver_spending_changes_logic():
    # BUG 2 verified
    profile = FinancialProfile("u1", "USD", Decimal("120"), Decimal("0"), [], [], ["Dining"], ["Entertainment"], ["full_payment"], None)
    state = {
        "recurring_expenses": [
            {
                "description": "Netflix", "direction": "debit", "category": "Entertainment",
                "flexibility": "stoppable", "amount": Decimal("15"), "frequency_days": 30,
                "next_date": date(2026, 9, 15), "last_event_id": "e1", "minimum_allowed_amount": None
            },
            {
                "description": "Food", "direction": "debit", "category": "Dining",
                "flexibility": "reducible", "amount": Decimal("100"), "frequency_days": 30,
                "next_date": date(2026, 9, 15), "last_event_id": "e2", "minimum_allowed_amount": Decimal("50")
            }
        ],
        "recurring_incomes": [
            {
                "description": "Salary", "direction": "credit", "category": "Income",
                "flexibility": "fixed", "amount": Decimal("1000"), "frequency_days": 30,
                "next_date": date(2026, 9, 14), "last_event_id": "e3", "minimum_allowed_amount": None
            }
        ],
        "explicit_future_events": []
    }
    sim = Simulator(profile, state)
    req = Request("r1", "u1", date(2026, 9, 13), "purchase", Decimal("50"), date(2026, 12, 1), False, "")
    
    solver = Solver(sim, req, [])
    # _find_amount_safe uses spending_changes param
    candidates, amt, e_date = solver.generate_candidate_plans()
    
    changes = []
    for c in candidates:
        for sc in c["spending_changes"]:
            changes.append(sc["type"])
            
    assert "stop" in changes
    assert "reduce_to" in changes
