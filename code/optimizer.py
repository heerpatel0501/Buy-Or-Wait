from typing import List, Dict, Any
from code.models import FinancialProfile

class Optimizer:
    def __init__(self, profile: FinancialProfile):
        self.profile = profile
        
    def format_plan_string(self, plan: Dict) -> str:
        if not plan:
            return "none"
        dates = sorted(plan.keys())
        return "|".join([f"{d.isoformat()}:{plan[d]:.2f}".rstrip('0').rstrip('.') for d in dates])
        
    def rank_plans(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ranks plans by:
        1. User accepts the method
        2. No spending changes (implicit for now)
        3. Minimize total amount paid
        4. Start payment earlier
        5. Fewer payments
        6. Lowest option_id
        """
        allowed = self.profile.payment_methods_user_will_consider
        valid = [c for c in candidates if c['method'] in allowed or (c['method'] == 'wait' and 'full_payment' in allowed)]
        
        if not valid:
            return None
            
        def sort_key(c):
            plan_dates = sorted(c['plan'].keys())
            first_payment = plan_dates[0].isoformat() if plan_dates else "9999-12-31"
            num_payments = len(plan_dates)
            opt_id = c['option_id'] or "zzzzzz"
            changes = len(c['spending_changes'])
            
            return (
                changes,
                c['total_paid'],
                first_payment,
                num_payments,
                opt_id
            )
            
        valid.sort(key=sort_key)
        best = valid[0]
        
        # Format for output
        best['plan_string'] = self.format_plan_string(best['plan'])
        return best
