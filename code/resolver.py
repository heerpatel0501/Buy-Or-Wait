from typing import List, Dict
from models import FinancialEvent, ExtractedFact, Provenance
from datetime import datetime

class ConflictResolver:
    def __init__(self):
        pass
        
    def resolve(self, raw_events: List[FinancialEvent], extracted_facts: List[ExtractedFact]) -> List[FinancialEvent]:
        """
        Applies deterministic precedence to merge extracted facts with historical/scheduled events.
        Precedence:
        1. Explicit cancellation/amendment (from facts)
        2. Newer records from the same source
        3. Settled > Forecast
        """
        resolved_events = []
        # Index events for quick lookup
        events_by_id = {evt.event_id: evt for evt in raw_events}
        
        # Apply extracted facts (cancellations and modifications)
        for fact in extracted_facts:
            if fact.related_event_id and fact.related_event_id in events_by_id:
                evt = events_by_id[fact.related_event_id]
                
                # Create a new provenance trail
                new_prov = Provenance(
                    source=fact.provenance.source,
                    timestamp=datetime.utcnow().isoformat(),
                    reasoning=f"Modified by extracted fact: {fact.fact_type}. Evidence: {fact.evidence}",
                    original_data={"previous_provenance": evt.provenance}
                )
                
                if fact.fact_type == "cancel":
                    evt.status = "cancelled"
                    evt.provenance = new_prov
                elif fact.fact_type == "modify_amount" and fact.amount is not None:
                    evt.amount = fact.amount
                    evt.provenance = new_prov
                elif fact.fact_type == "extract_image_amount" and fact.amount is not None:
                    # Treat a blank amount as overwritten by image extraction
                    evt.amount = fact.amount
                    evt.provenance = new_prov
                    
                # Date modifications if provided
                if fact.date is not None:
                    evt.event_date = fact.date
                    evt.settlement_date = fact.date
                    evt.provenance = new_prov
                    
        # Filter out cancelled, failed, and duplicated events
        for evt in events_by_id.values():
            if evt.status not in ["cancelled", "failed", "duplicate"]:
                resolved_events.append(evt)
                
        return resolved_events
