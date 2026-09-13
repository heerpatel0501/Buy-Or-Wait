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
        
    def find_amount_safe_to_pay(self, spending_changes=None) -> Decimal:
        """
        Uses binary search or monotonic feasibility to find max safe amount today.
        """
        low = Decimal(0)
        high = self.request.requested_amount
        best = Decimal(0)
        
        # Simple binary search (down to 2 decimal places)
        while high - low >= Decimal('0.01'):
            mid = (low + high) / Decimal(2)
            mid = round(mid, 2)
            
            is_safe, _ = self.simulator.simulate(
                self.request.request_date, 
                {self.request.request_date: mid}, 
                spending_changes
            )
            
            if is_safe:
                best = mid
                low = mid + Decimal('0.01')
            else:
                high = mid - Decimal('0.01')
                
        return best

    def find_earliest_full_payment_date(self) -> str:
        """
        Finds earliest date full payment is safe without spending changes.
        """
        for i in range(91):
            test_date = self.request.request_date + timedelta(days=i)
            is_safe, _ = self.simulator.simulate(
                self.request.request_date, 
                {test_date: self.request.requested_amount}
            )
            if is_safe:
                return test_date.isoformat()
        return ""

    def generate_candidate_plans(self) -> List[Dict[str, Any]]:
        candidates = []
        earliest_full_date = self.find_earliest_full_payment_date()
        amount_safe = self.find_amount_safe_to_pay()
        
        # 1. Full Payment Now
        is_full_safe, _ = self.simulator.simulate(self.request.request_date, {self.request.request_date: self.request.requested_amount})
        if is_full_safe:
            candidates.append({
                "method": "full_payment",
                "plan": {self.request.request_date: self.request.requested_amount},
                "total_paid": self.request.requested_amount,
                "spending_changes": [],
                "option_id": None
            })
            
        # 2. Partial Payment
        if self.request.allows_partial_payment and amount_safe > 0 and amount_safe < self.request.requested_amount:
            if earliest_full_date:
                e_date = date.fromisoformat(earliest_full_date)
                if e_date <= self.request.desired_completion_date:
                    plan = {
                        self.request.request_date: amount_safe,
                        e_date: self.request.requested_amount - amount_safe
                    }
                    is_part_safe, _ = self.simulator.simulate(self.request.request_date, plan)
                    if is_part_safe:
                        candidates.append({
                            "method": "partial_payment",
                            "plan": plan,
                            "total_paid": self.request.requested_amount,
                            "spending_changes": [],
                            "option_id": None
                        })
                        
        # 3. Wait
        if earliest_full_date:
            e_date = date.fromisoformat(earliest_full_date)
            if e_date <= self.request.desired_completion_date and e_date > self.request.request_date:
                plan = {e_date: self.request.requested_amount}
                candidates.append({
                    "method": "wait",
                    "plan": plan,
                    "total_paid": self.request.requested_amount,
                    "spending_changes": [],
                    "option_id": None
                })
                
        # 4. Installments
        for opt in self.payment_options:
            if opt.payment_method == "installments":
                plan = {}
                for i in range(opt.number_of_payments):
                    p_date = opt.first_payment_date + timedelta(days=i * (opt.payment_frequency_days or 30))
                    plan[p_date] = opt.payment_amount
                
                is_inst_safe, _ = self.simulator.simulate(self.request.request_date, plan)
                # Check completion date
                last_payment_date = max(plan.keys())
                if is_inst_safe and last_payment_date <= self.request.desired_completion_date:
                    candidates.append({
                        "method": "installments",
                        "plan": plan,
                        "total_paid": opt.total_payable_amount,
                        "spending_changes": [],
                        "option_id": opt.payment_option_id
                    })
                    
        return candidates, amount_safe, earliest_full_date
