from typing import List, Dict, Any, Tuple
from decimal import Decimal
from datetime import date, timedelta
from code.models import Request, PaymentOption
from code.simulator import Simulator

class Solver:
    def __init__(self, simulator: Simulator, request: Request, payment_options: List[PaymentOption]):
        self.simulator = simulator
        self.request = request
        self.payment_options = payment_options
        
    def generate_candidate_plans(self) -> Tuple[List[Dict[str, Any]], Decimal, str]:
        amount_safe = self._find_amount_safe(spending_changes=[])
        earliest_full_date = self._find_earliest_full(spending_changes=[])
        
        candidates = []
        
        profile = self.simulator.profile
        state = self.simulator.state
        import itertools
        possible_changes = [[]] # No changes
        
        single_changes = []
        flex_reduce = profile.expense_categories_user_is_willing_to_reduce
        flex_stop = profile.expense_categories_user_is_willing_to_stop
        
        for exp in state['recurring_expenses']:
            flex = exp['flexibility']
            can_stop = (flex in ['stoppable', 'reducible_or_stoppable'])
            can_reduce = (flex in ['reducible', 'reducible_or_stoppable'])
            
            # Use lower() and strip() just in case
            cat = str(exp['category']).strip().lower()
            flex_stop_clean = [c.strip().lower() for c in flex_stop]
            flex_reduce_clean = [c.strip().lower() for c in flex_reduce]
            
            if can_stop and cat in flex_stop_clean:
                single_changes.append({'type': 'stop', 'target_event_id': exp['last_event_id']})
                
            if can_reduce and cat in flex_reduce_clean and exp['minimum_allowed_amount'] is not None:
                single_changes.append({'type': 'reduce_to', 'target_event_id': exp['last_event_id'], 'new_amount': exp['minimum_allowed_amount']})
                    
        # Generate combinations of up to 3 changes
        for i in range(1, min(4, len(single_changes) + 1)):
            for combo in itertools.combinations(single_changes, i):
                # Ensure no duplicate targets in the same combo
                targets = [c['target_event_id'] for c in combo]
                if len(targets) == len(set(targets)):
                    possible_changes.append(list(combo))
        
        for sc in possible_changes:
            if "full_payment" in profile.payment_methods_user_will_consider:
                is_full, _ = self.simulator.simulate(self.request.request_date, {self.request.request_date: self.request.requested_amount}, sc)
                if is_full:
                    candidates.append({
                        "method": "full_payment",
                        "plan": {self.request.request_date: self.request.requested_amount},
                        "total_paid": self.request.requested_amount,
                        "spending_changes": sc,
                        "option_id": None
                    })
                    
            if "partial_payment" in profile.payment_methods_user_will_consider and self.request.allows_partial_payment:
                if amount_safe > 0 and amount_safe < self.request.requested_amount:
                    e_date = earliest_full_date
                    if not e_date: e_date = self._find_earliest_full(sc)
                    if e_date:
                        ed = date.fromisoformat(e_date)
                        if ed <= self.request.desired_completion_date:
                            plan = {
                                self.request.request_date: amount_safe,
                                ed: self.request.requested_amount - amount_safe
                            }
                            is_part, _ = self.simulator.simulate(self.request.request_date, plan, sc)
                            if is_part:
                                candidates.append({
                                    "method": "partial_payment",
                                    "plan": plan,
                                    "total_paid": self.request.requested_amount,
                                    "spending_changes": sc,
                                    "option_id": None
                                })
                                
            if "installments" in profile.payment_methods_user_will_consider:
                for opt in self.payment_options:
                    if opt.payment_method == "installments":
                        plan = {}
                        for i in range(opt.number_of_payments):
                            p_date = opt.first_payment_date + timedelta(days=i * (opt.payment_frequency_days or 30))
                            plan[p_date] = opt.payment_amount
                        is_inst, _ = self.simulator.simulate(self.request.request_date, plan, sc)
                        last_date = max(plan.keys()) if plan else self.request.request_date
                        if is_inst and last_date <= self.request.desired_completion_date:
                            candidates.append({
                                "method": "installments",
                                "plan": plan,
                                "total_paid": opt.total_payable_amount,
                                "spending_changes": sc,
                                "option_id": opt.payment_option_id
                            })
                            
            if "wait" in profile.payment_methods_user_will_consider or "full_payment" in profile.payment_methods_user_will_consider:
                e_date = self._find_earliest_full(sc)
                if e_date:
                    ed = date.fromisoformat(e_date)
                    if self.request.request_date < ed <= self.request.desired_completion_date:
                        plan = {ed: self.request.requested_amount}
                        is_wait, _ = self.simulator.simulate(self.request.request_date, plan, sc)
                        if is_wait:
                            candidates.append({
                                "method": "wait",
                                "plan": plan,
                                "total_paid": self.request.requested_amount,
                                "spending_changes": sc,
                                "option_id": None
                            })
                            
        return candidates, amount_safe, earliest_full_date
        
    def _find_amount_safe(self, spending_changes) -> Decimal:
        low = Decimal(0)
        high = self.request.requested_amount
        best = Decimal(0)
        while high - low >= Decimal('0.01'):
            mid = round((low + high) / Decimal(2), 2)
            is_safe, _ = self.simulator.simulate(self.request.request_date, {self.request.request_date: mid}, spending_changes)
            if is_safe:
                best = mid
                low = mid + Decimal('0.01')
            else:
                high = mid - Decimal('0.01')
        return best

    def _find_earliest_full(self, spending_changes) -> str:
        for i in range(91):
            d = self.request.request_date + timedelta(days=i)
            is_safe, _ = self.simulator.simulate(self.request.request_date, {d: self.request.requested_amount}, spending_changes)
            if is_safe:
                return d.isoformat()
        return ""
