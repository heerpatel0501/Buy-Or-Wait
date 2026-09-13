from typing import Dict, Any
from code.models import Request
from code.simulator import Simulator
from decimal import Decimal
from datetime import date

class Verifier:
    def __init__(self, simulator: Simulator, request: Request):
        self.simulator = simulator
        self.request = request
        
    def verify(self, output_row: Dict[str, str], best_plan: Dict[str, Any]) -> bool:
        if output_row['affordability_status'] == 'not_affordable':
            return output_row['recommended_payment_method'] == 'not_recommended' and output_row['payment_plan'] == 'none'
            
        try:
            amt_safe = Decimal(output_row['amount_safe_to_pay'])
            if not (Decimal(0) <= amt_safe <= self.request.requested_amount):
                return False
                
            if output_row['affordability_status'] == 'affordable_now':
                if output_row['earliest_date_for_full_payment'] != self.request.request_date.isoformat():
                    return False
                    
            if best_plan:
                # BUG 6: Verify payment totals
                method = best_plan.get('method')
                if method in ['full_payment', 'partial_payment', 'wait']:
                    total = sum(best_plan['plan'].values())
                    if abs(total - self.request.requested_amount) > Decimal('0.01'):
                        return False
                        
                is_safe, _ = self.simulator.simulate(self.request.request_date, best_plan['plan'], best_plan.get('spending_changes', []))
                if not is_safe:
                    return False
                    
                last_date = max(best_plan['plan'].keys()) if best_plan['plan'] else self.request.request_date
                if last_date > self.request.desired_completion_date:
                    return False
                    
            return True
        except Exception:
            return False
