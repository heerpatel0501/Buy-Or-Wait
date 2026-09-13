import pytest
from code.simulator import Simulator
from code.models import FinancialProfile
from decimal import Decimal
from datetime import date

def test_simulator_minimum_balance_exact():
    profile = FinancialProfile("u1", "USD", Decimal("100"), Decimal("20"), [], [], [], [], [], None)
    state = {
        "recurring_expenses": [],
        "recurring_incomes": [],
        "explicit_future_events": []
    }
    sim = Simulator(profile, state)
    
    # 100 - 80 = 20, exactly minimum balance, should be safe
    plan = {date(2026, 9, 13): Decimal("80")}
    is_safe, _ = sim.simulate(date(2026, 9, 13), plan, [])
    assert is_safe is True
    
    # 100 - 80.01 = 19.99, below minimum balance, should be unsafe
    plan = {date(2026, 9, 13): Decimal("80.01")}
    is_safe, _ = sim.simulate(date(2026, 9, 13), plan, [])
    assert is_safe is False
