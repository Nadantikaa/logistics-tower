from pydantic import BaseModel, Field

from app.models.shipment import CongestionLevel, Shipment


class AffectedShipment(BaseModel):
    id: str
    delay_increase: float = Field(ge=0)
    reason: str = ""


class RippleEffect(BaseModel):
    primary_delay_increase: int
    affected_shipments: list[AffectedShipment]
    summary: dict


def simulate_ripple_effect(primary_shipment: Shipment, all_shipments: list[Shipment]) -> RippleEffect:
    """
    Simulate ripple effect of a primary shipment's delay on dependent shipments.
    
    Rules:
    - If congestion = HIGH → propagate to 1–2 dependent shipments
    - If delay_probability > 0.8 → increase delay by 1–3 hours
    - If shared_resource matches → amplify delay impact
    """
    affected = []
    
    # Get primary shipment parameters
    congestion_level = primary_shipment.signals.port_congestion_level
    delay_prob = primary_shipment.ml_output.delay_probability / 100.0
    shared_resource = primary_shipment.shared_resource
    
    # Compute primary delay increase
    primary_delay_increase = 0
    if congestion_level == "HIGH":
        primary_delay_increase = 4
    elif congestion_level == "MEDIUM":
        primary_delay_increase = 2
    else:
        primary_delay_increase = 1
    
    # If high delay probability, add more delay
    if delay_prob > 0.8:
        primary_delay_increase += 3
    elif delay_prob > 0.6:
        primary_delay_increase += 1
    
    # Process dependent shipments
    for dependent_id in primary_shipment.dependent_shipments:
        # Find the dependent shipment
        dependent_shipment = next(
            (s for s in all_shipments if s.shipment_id == dependent_id),
            None
        )
        
        if not dependent_shipment:
            continue
        
        # Calculate delay propagation
        delay_increase = 0
        reason = ""
        
        # Base propagation: 50% of primary delay
        delay_increase = primary_delay_increase * 0.5
        reason = f"Dependent on {primary_shipment.shipment_id}"
        
        # Amplify if shared resource
        if shared_resource and dependent_shipment.shared_resource == shared_resource:
            delay_increase *= 1.5
            reason += f"; sharing {shared_resource}"
        
        # Amplify based on congestion
        if congestion_level == "HIGH":
            delay_increase = min(delay_increase + 1, 2)  # Cap at 2 hours additional
        
        # High delay probability propagation
        if delay_prob > 0.8:
            delay_increase = min(delay_increase + 1, 3)
        
        affected.append(
            AffectedShipment(
                id=dependent_id,
                delay_increase=round(delay_increase, 1),
                reason=reason
            )
        )
    
    # Limit affected shipments based on congestion
    if congestion_level == "HIGH":
        affected = affected[:2]  # Max 2 affected in HIGH congestion
    elif congestion_level == "MEDIUM":
        affected = affected[:1]  # Max 1 affected in MEDIUM congestion
    
    # Compute summary
    summary = {
        "total_affected": len(affected),
        "max_delay": max([a.delay_increase for a in affected], default=0),
    }
    
    return RippleEffect(
        primary_delay_increase=primary_delay_increase,
        affected_shipments=affected,
        summary=summary
    )
