import pytest
from code.resolver import ConflictResolver
from code.models import FinancialEvent, ExtractedFact, Provenance
from decimal import Decimal
from datetime import date

def test_resolver_precedence_rules():
    # BUG 8 verified
    resolver = ConflictResolver()
    events = [
        FinancialEvent("e1", "u1", "transfer", "desc", "cat", "debit", Decimal("100"), "USD", date(2026, 9, 13), None, "estimate", None, "fixed", None),
        FinancialEvent("e1", "u1", "transfer", "desc", "cat", "debit", Decimal("200"), "USD", date(2026, 9, 13), None, "settled", None, "fixed", None)
    ]
    # Conflict between estimate and settled with SAME event_id
    res = resolver.resolve(events, [])
    assert len(res) == 1
    assert res[0].amount == Decimal("200")
    assert res[0].status == "settled"
    
    # Check LLM fact precedence
    facts = [
        ExtractedFact("e1", "cancellation", None, None, "", Provenance("llm", "", Decimal("1.0"), ""))
    ]
    res2 = resolver.resolve(events, facts)
    assert len(res2) == 1
    assert res2[0].status == "cancelled"
