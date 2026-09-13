from typing import List, Dict, Any, Tuple
from decimal import Decimal
from datetime import date, timedelta
from models import FinancialProfile

class Simulator:
    def __init__(self, profile: FinancialProfile, state: Dict[str, Any]):
        self.profile = profile
        self.state = state
        
    def simulate(self, start_date: date, payment_plan: Dict[date, Decimal], spending_changes: List[Dict[str, Any]] = None) -> Tuple[bool, Decimal]:
        """
        Simulates 90 days of transactions.
        Returns (is_safe, lowest_balance)
        """
        if spending_changes is None:
            spending_changes = []
            
        current_balance = self.profile.current_available_balance
        lowest_balance = current_balance
        min_required = self.profile.minimum_balance_to_keep
        
        # Build timeline of events for 90 days
        timeline = {start_date + timedelta(days=i): Decimal(0) for i in range(91)}
        
        # Apply payment plan
        for p_date, p_amt in payment_plan.items():
            if p_date in timeline:
                timeline[p_date] -= p_amt
                
        # Helper to apply spending changes
        def get_modified_expense(rec_expense):
            for change in spending_changes:
                if change['type'] == 'stop' and change['target_event_id'] == rec_expense['last_event_id']:
                    return Decimal(0)
                if change['type'] == 'reduce_to' and change['target_event_id'] == rec_expense['last_event_id']:
                    return Decimal(str(change['new_amount']))
            return Decimal(str(rec_expense['amount']))

        # Project Recurring Incomes
        for inc in self.state['recurring_incomes']:
            curr = inc['next_date']
            while curr <= start_date + timedelta(days=90):
                if curr >= start_date:
                    timeline[curr] += Decimal(str(inc['amount']))
                curr += timedelta(days=inc['frequency_days'])
                
        # Project Recurring Expenses
        for exp in self.state['recurring_expenses']:
            # Skip if not in protected categories (Wait, problem says ONLY flexible expenses can be changed, 
            # and we must cover essential expenses. By default, assume all recurring are essential unless flexed).
            curr = exp['next_date']
            mod_amt = get_modified_expense(exp)
            while curr <= start_date + timedelta(days=90):
                if curr >= start_date:
                    timeline[curr] -= mod_amt
                curr += timedelta(days=exp['frequency_days'])
                
        # Project Explicit Future Events
        for evt in self.state['explicit_future_events']:
            if start_date <= evt.event_date <= start_date + timedelta(days=90):
                if evt.direction == 'credit':
                    timeline[evt.event_date] += evt.amount
                else:
                    timeline[evt.event_date] -= evt.amount
                    
        # Simulate day by day
        for i in range(91):
            curr_date = start_date + timedelta(days=i)
            current_balance += timeline[curr_date]
            if current_balance < lowest_balance:
                lowest_balance = current_balance
            
            if current_balance < min_required:
                return False, lowest_balance
                
        return True, lowest_balance
