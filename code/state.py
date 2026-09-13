from typing import List, Dict, Any, Tuple
from code.models import FinancialEvent, Request, FinancialProfile
from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict

class FinancialStateLayer:
    def __init__(self):
        pass

    def reconstruct(self, resolved_events: List[FinancialEvent], request: Request) -> Dict[str, Any]:
        """
        Reconstructs the canonical financial state on the request_date.
        Identifies recurring expenses, recurring incomes, and future one-off events.
        """
        past_events = [e for e in resolved_events if e.event_date <= request.request_date]
        future_events = [e for e in resolved_events if e.event_date > request.request_date]
        
        # 1. Infer Recurring Events from past history
        # Group by description and direction
        groups = defaultdict(list)
        for e in past_events:
            if e.status == 'settled':
                groups[(e.description, e.direction, e.category, e.flexibility)].append(e)
                
        recurring_expenses = []
        recurring_incomes = []
        
        for key, events in groups.items():
            if len(events) >= 2:
                events.sort(key=lambda x: x.event_date)
                # Calculate average frequency
                intervals = [(events[i].event_date - events[i-1].event_date).days for i in range(1, len(events))]
                avg_interval = sum(intervals) / len(intervals)
                
                # If avg_interval is stable enough (e.g. weekly ~7, monthly ~30)
                if 5 <= avg_interval <= 40:
                    last_event = events[-1]
                    # Forecast the next date
                    next_date = last_event.event_date + timedelta(days=round(avg_interval))
                    
                    # Ensure next_date is past or equal to request_date
                    while next_date < request.request_date:
                        next_date += timedelta(days=round(avg_interval))
                        
                    # Compute average amount for forecasting
                    avg_amt = sum(e.amount for e in events) / len(events)
                    
                    rec_event = {
                        "description": key[0],
                        "direction": key[1],
                        "category": key[2],
                        "flexibility": key[3],
                        "amount": avg_amt,
                        "frequency_days": round(avg_interval),
                        "next_date": next_date,
                        "last_event_id": last_event.event_id,
                        "minimum_allowed_amount": last_event.minimum_allowed_amount
                    }
                    if key[1] == 'debit':
                        recurring_expenses.append(rec_event)
                    else:
                        recurring_incomes.append(rec_event)

        # 2. Extract explicit future scheduled events (e.g., "Next confirmed salary")
        explicit_future = []
        for e in future_events:
            if e.status in ['scheduled', 'pending']:
                explicit_future.append(e)
                
        # Merge logic to avoid double-counting
        # If an explicit future event exists for a recurring description, we remove that specific forecast for the next cycle,
        # or we just let the explicit event replace the forecast.
        filtered_recurring_incomes = []
        for inc in recurring_incomes:
            # Check if there is an explicit future event matching this description
            has_explicit = any(e.description == inc['description'] for e in explicit_future)
            if not has_explicit:
                filtered_recurring_incomes.append(inc)
                
        filtered_recurring_expenses = []
        for exp in recurring_expenses:
            has_explicit = any(e.description == exp['description'] for e in explicit_future)
            if not has_explicit:
                filtered_recurring_expenses.append(exp)
        
        return {
            "recurring_expenses": filtered_recurring_expenses,
            "recurring_incomes": filtered_recurring_incomes,
            "explicit_future_events": explicit_future
        }
