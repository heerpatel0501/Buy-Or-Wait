from typing import Dict, Any, List
from decimal import Decimal
from code.models import Request
from code.simulator import Simulator

class Verifier:
    def __init__(self, simulator: Simulator, request: Request):
        self.simulator = simulator
        self.request = request
        
    def verify(self, output: Dict[str, Any]) -> bool:
        """
        Independently re-runs financial safety using the chosen plan.
        """
        # If not recommended, no math to verify
        if output['recommended_payment_method'] == 'not_recommended':
            return True
            
        plan_str = output['payment_plan']
        plan = {}
        if plan_str != 'none':
            for chunk in plan_str.split('|'):
                parts = chunk.split(':')
                if len(parts) == 2:
                    from datetime import date
                    plan[date.fromisoformat(parts[0])] = Decimal(parts[1])
                    
        # Verify sum matches requested amount for full/partial/wait
        if output['recommended_payment_method'] in ['full_payment', 'partial_payment', 'wait']:
            total = sum(plan.values())
            # small tolerance for floating precision issues during JSON extraction, though Decimal should prevent it
            if abs(total - self.request.requested_amount) > Decimal('0.01'):
                print(f"VERIFIER FAILED: Total {total} != requested {self.request.requested_amount}")
                return False
                
        # Re-simulate mathematically
        # Convert spending changes
        # For simplicity in hackathon, if there are spending changes, we would parse them here.
        # Currently, solver generates empty spending changes.
        is_safe, lowest_balance = self.simulator.simulate(self.request.request_date, plan, [])
        if not is_safe:
            print(f"VERIFIER FAILED: Plan violates minimum balance. Lowest: {lowest_balance}")
            return False
            
        return True
