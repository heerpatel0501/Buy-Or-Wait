from typing import List
from code.models import FinancialEvent, ExtractedFact
import copy

class ConflictResolver:
    def resolve(self, events: List[FinancialEvent], facts: List[ExtractedFact]) -> List[FinancialEvent]:
        # BUG 8: Implement strict precedence logic
        
        resolved = {}
        # First group events from CSV by event_id or linked_event_id conceptually.
        # The prompt says: 1. explicit cancellation/settlement/amendment (facts) 2. newer record 3. settled > estimate
        # 4. safer interpretation
        
        # Step 1: Pre-process CSV events, resolving CSV-level conflicts
        # Keep the latest timestamped event if there are exact duplicates? (Not easily possible without timestamps in CSV)
        # We will just index them for now.
        for e in events:
            if e.event_id in resolved:
                # Conflict in CSV: Rule 3: settled > estimate/forecast
                old_e = resolved[e.event_id]
                if e.status == 'settled' and old_e.status != 'settled':
                    resolved[e.event_id] = e
                elif old_e.status == 'settled' and e.status != 'settled':
                    pass
                else:
                    # Rule 4: Financially safer interpretation
                    if e.direction == 'debit' and old_e.direction == 'debit':
                        # Higher debit is safer
                        if e.amount > old_e.amount: resolved[e.event_id] = e
                    elif e.direction == 'credit' and old_e.direction == 'credit':
                        # Lower credit is safer
                        if e.amount < old_e.amount: resolved[e.event_id] = e
            else:
                resolved[e.event_id] = copy.deepcopy(e)
                
        # Step 2: Apply LLM Facts (Rule 1 & 2 implicitly as they are newer amendments)
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
