from typing import List, Dict, Any
from code.models import FinancialProfile, Request

class Optimizer:
    def __init__(self, profile: FinancialProfile, request: Request):
        self.profile = profile
        self.request = request
        
    def rank_plans(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            return None
            
        def rank_key(c):
            # 1. Complete by desired_completion_date
            last_date = max(c['plan'].keys())
            c1 = last_date <= self.request.desired_completion_date
            
            # 2. No spending changes
            c2 = len(c['spending_changes']) == 0
            
            # 3. Minimize total amount paid
            c3 = c['total_paid']
            
            # 4. Earliest payment start
            c4 = min(c['plan'].keys())
            
            # 5. Fewest payments
            c5 = len(c['plan'])
            
            # 6. Lowest payment_option_id
            opt = c['option_id'] or "Z"
            
            # False sorts before True, so we negate bools for "True is better"
            return (not c1, not c2, c3, c4, c5, opt)
            
        ranked = sorted(candidates, key=rank_key)
        best = ranked[0]
        
        # Serialize plan
        plan_strs = []
        for d in sorted(best['plan'].keys()):
            plan_strs.append(f"{d.isoformat()}:{best['plan'][d]}")
        best['plan_string'] = "|".join(plan_strs)
        
        return best
