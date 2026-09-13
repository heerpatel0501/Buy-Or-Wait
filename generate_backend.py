import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
        f.write('\n')
        
state_py = """
from typing import List, Dict, Any, Tuple
from code.models import FinancialEvent, Request, FinancialProfile
from decimal import Decimal
from datetime import date, timedelta
from collections import defaultdict
import pandas as pd

class FinancialStateLayer:
    def __init__(self, exchange_rates_df=None):
        self.exchange_rates_df = exchange_rates_df

    def reconstruct(self, resolved_events: List[FinancialEvent], request: Request, profile: FinancialProfile) -> Dict[str, Any]:
        past_events = [e for e in resolved_events if e.event_date <= request.request_date]
        future_events = [e for e in resolved_events if e.event_date > request.request_date]
        
        groups = defaultdict(list)
        for e in past_events:
            if e.status == 'settled':
                groups[(e.description, e.direction, e.category, e.flexibility)].append(e)
                
        recurring_expenses = []
        recurring_incomes = []
        
        for key, events in groups.items():
            if len(events) >= 2:
                events.sort(key=lambda x: x.event_date)
                intervals = [(events[i].event_date - events[i-1].event_date).days for i in range(1, len(events))]
                avg_interval = sum(intervals) / len(intervals)
                
                if 5 <= avg_interval <= 40:
                    last_event = events[-1]
                    next_date = last_event.event_date + timedelta(days=round(avg_interval))
                    
                    while next_date <= request.request_date:
                        next_date += timedelta(days=round(avg_interval))
                        
                    avg_amt = sum(e.amount for e in events) / len(events)
                    
                    # Convert to home_currency
                    converted_amt = self._convert(avg_amt, last_event.currency, profile.home_currency, last_event.settlement_date or last_event.event_date)
                    
                    rec_event = {
                        "description": key[0],
                        "direction": key[1],
                        "category": key[2],
                        "flexibility": key[3],
                        "amount": converted_amt,
                        "frequency_days": round(avg_interval),
                        "next_date": next_date,
                        "last_event_id": last_event.event_id,
                        "minimum_allowed_amount": self._convert(last_event.minimum_allowed_amount, last_event.currency, profile.home_currency, last_event.settlement_date or last_event.event_date) if last_event.minimum_allowed_amount else None
                    }
                    if key[1] == 'debit':
                        recurring_expenses.append(rec_event)
                    else:
                        recurring_incomes.append(rec_event)

        explicit_future = []
        for e in future_events:
            if e.status in ['scheduled', 'pending', 'confirmed']:
                # convert
                converted_amt = self._convert(e.amount, e.currency, profile.home_currency, e.settlement_date or e.event_date)
                e.amount = converted_amt
                e.currency = profile.home_currency
                explicit_future.append(e)
                
        filtered_recurring_incomes = []
        for inc in recurring_incomes:
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
        
    def _convert(self, amount, from_currency, to_currency, rate_date):
        if amount is None or amount == Decimal('0.0'): return Decimal('0.0')
        if from_currency == to_currency: return amount
        if self.exchange_rates_df is None or self.exchange_rates_df.empty:
            return amount
        rates = self.exchange_rates_df
        rd_str = rate_date.strftime('%Y-%m-%d')
        match = rates[(rates['rate_date'] == rd_str) & (rates['from_currency'] == from_currency) & (rates['to_currency'] == to_currency)]
        if not match.empty:
            rate = Decimal(str(match.iloc[0]['rate']))
            return amount * rate
        return amount
"""
write_file('code/state.py', state_py)
