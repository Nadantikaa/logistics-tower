from pydantic import BaseModel, Field

from app.models.shipment import ActionType


class SimulationRequest(BaseModel):
    action: ActionType


class AffectedShipmentInfo(BaseModel):
    id: str
    delay_increase: float = Field(ge=0)
    reason: str = ""


class RippleEffectSummary(BaseModel):
    total_affected: int = 0
    max_delay: float = 0


class SimulationResult(BaseModel):
    action: ActionType
    baseline_eta: str
    simulated_eta: str
    baseline_delay_probability: int = Field(ge=0, le=100)
    simulated_delay_probability: int = Field(ge=0, le=100)
    baseline_risk_score: int = Field(ge=0, le=100)
    simulated_risk_score: int = Field(ge=0, le=100)
    impact_summary: str
    # Ripple effect fields
    primary_delay_increase: int = 0
    affected_shipments: list[AffectedShipmentInfo] = Field(default_factory=list)
    ripple_summary: RippleEffectSummary = Field(default_factory=RippleEffectSummary)
