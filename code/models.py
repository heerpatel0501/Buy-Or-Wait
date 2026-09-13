from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date, datetime

@dataclass
class Provenance:
    source: str  # e.g., "csv", "llm_message", "llm_image", "conflict_resolver"
    timestamp: str
    confidence: Decimal = Decimal('1.0')
    reasoning: str = ""
    original_data: Optional[Dict[str, Any]] = None

@dataclass
class FinancialProfile:
    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    financial_priorities: List[str]
    expense_categories_to_protect: List[str]
    expense_categories_user_is_willing_to_reduce: List[str]
    expense_categories_user_is_willing_to_stop: List[str]
    payment_methods_user_will_consider: List[str]
    max_installment_months: Optional[int]

@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str
    amount: Decimal
    currency: str
    event_date: date
    settlement_date: date
    status: str
    linked_event_id: Optional[str]
    flexibility: str
    minimum_allowed_amount: Optional[Decimal]
    provenance: Provenance = field(default_factory=lambda: Provenance("csv", datetime.utcnow().isoformat()))
    
@dataclass
class PaymentOption:
    payment_option_id: str
    payment_method: str
    payment_amount: Decimal
    number_of_payments: int
    first_payment_date: date
    payment_frequency_days: Optional[int]
    total_payable_amount: Decimal

@dataclass
class Request:
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str

@dataclass
class ExtractedFact:
    related_event_id: Optional[str]
    fact_type: str
    amount: Optional[Decimal]
    date: Optional[date]
    evidence: str
    provenance: Provenance

@dataclass
class FinancialCase:
    request: Request
    profile: FinancialProfile
    events: List[FinancialEvent]
    payment_options: List[PaymentOption]
    extracted_facts: List[ExtractedFact]
    resolved_events: List[FinancialEvent] = field(default_factory=list)

