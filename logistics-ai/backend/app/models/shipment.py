from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
ActionType = Literal["REROUTE", "HOLD", "SWITCH CARRIER", "EXPEDITE", "NO ACTION"]
CongestionLevel = Literal["LOW", "MEDIUM", "HIGH"]


class ShipmentSignal(BaseModel):
    weather_status: str
    temperature_c: float | None = None
    port_congestion_level: CongestionLevel
    news_tags: list[str] = Field(default_factory=list)
    shipment_status: str


class MlOutput(BaseModel):
    eta_prediction: str
    delay_probability: int = Field(ge=0, le=100)
    anomaly_score: int = Field(ge=0, le=100)
    risk_score: int = Field(ge=0, le=100)


class DecisionOutput(BaseModel):
    action: ActionType
    confidence: int = Field(ge=0, le=100)
    reason: str
    alert: str
    source: Literal["llm", "fallback"]
    updated_due_to_critical_change: bool = False
    # Ripple effects for recommended action (static baseline)
    primary_delay_increase: int = 0
    affected_shipments_ripple: list = Field(default_factory=list)  # list[AffectedShipmentInfo] from simulation module
    ripple_summary: dict = Field(default_factory=dict)


ExecutionStatus = Literal["EXECUTED", "PENDING", "FAILED"]


class Shipment(BaseModel):
    shipment_id: str
    origin: str
    destination: str
    current_location: str
    status: str
    priority: int = Field(ge=0, le=100)
    is_critical: bool = False
    risk_level: RiskLevel
    signals: ShipmentSignal
    ml_output: MlOutput
    decision: DecisionOutput | None = None
    # Dependency modeling fields
    dependent_shipments: list[str] = Field(default_factory=list)
    shared_resource: str = ""
    execution_status: ExecutionStatus = "PENDING"
    predicted_delay_hours: int = 0


class ShipmentSeed(BaseModel):
    shipment_id: str
    origin: str
    destination: str
    current_location: str
    status: str
    priority_base: int = Field(ge=0, le=100)
    is_critical: bool = False
    route_type: str = "Sea"
    baseline_eta_hours: int = Field(gt=0)
    alternate_carrier_available: bool = False
    dependent_shipments: list[str] = Field(default_factory=list)
    shared_resource: str = ""
    execution_status: ExecutionStatus = "PENDING"
    predicted_delay_hours: int = 0


class DecisionContext(BaseModel):
    shipment_id: str
    priority: int = Field(ge=0, le=100)
    is_critical: bool
    current_location: str
    destination: str
    status: str
    signals: ShipmentSignal
    ml_output: MlOutput
    alternate_carrier_available: bool = False
    # Dependency context
    dependent_shipments: list[str] = Field(default_factory=list)
    shared_resource: str = ""
