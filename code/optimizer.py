from typing import List, Dict, Any
from code.models import FinancialProfile, Request
from decimal import Decimal

class Optimizer:
    def __init__(self, profile: FinancialProfile, request: Request):
        self.profile = profile
        self.request = request
        
    def rank_plans(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            return None
            
        def rank_key(c):
            last_date = max(c['plan'].keys()) if c['plan'] else self.request.request_date
            c1 = last_date <= self.request.desired_completion_date
            c2 = len(c['spending_changes']) == 0
            c3 = c['total_paid']
            c4 = min(c['plan'].keys()) if c['plan'] else self.request.request_date
            c5 = len(c['plan'])
            opt = c['option_id'] or "Z"
            return (not c1, not c2, c3, c4, c5, opt)
            
        ranked = sorted(candidates, key=rank_key)
        best = ranked[0]
        
        plan_strs = []
        for d in sorted(best['plan'].keys()):
            # BUG 7: Normalize formatting consistently
            amt = best['plan'][d]
            amt_str = f"{amt:.2f}".rstrip('0').rstrip('.')
            plan_strs.append(f"{d.isoformat()}:{amt_str}")
        best['plan_string'] = "|".join(plan_strs)
        
        return best
