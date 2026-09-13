from typing import List
from code.models import FinancialEvent, ExtractedFact
from decimal import Decimal
import copy

class ConflictResolver:
    def resolve(self, events: List[FinancialEvent], facts: List[ExtractedFact]) -> List[FinancialEvent]:
        # Simple implementation for now to pass structure
        # The prompt says: Messages/images can clarify, amend, cancel, delay, or confirm.
        resolved = {e.event_id: copy.deepcopy(e) for e in events}
        
        for fact in facts:
            if not fact.related_event_id or fact.related_event_id not in resolved:
                continue
                
            e = resolved[fact.related_event_id]
            if fact.fact_type == 'cancellation':
                e.status = 'cancelled'
            elif fact.fact_type == 'amendment':
                if fact.amount is not None:
                    e.amount = fact.amount
                if fact.date is not None:
                    e.event_date = fact.date
            elif fact.fact_type == 'delay':
                if fact.date is not None:
                    e.event_date = fact.date
            elif fact.fact_type == 'confirmation':
                e.status = 'confirmed'
            elif fact.fact_type == 'settlement':
                e.status = 'settled'
                if fact.date is not None:
                    e.settlement_date = fact.date
                if fact.amount is not None:
                    e.amount = fact.amount
                    
        return list(resolved.values())
