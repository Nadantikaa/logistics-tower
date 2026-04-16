from pydantic import BaseModel


class MonitoringSummary(BaseModel):
    top_priority_shipment_id: str
    active_alerts: int
    high_risk_shipments: int
    critical_summary: str


class DecisionLogItem(BaseModel):
    shipment_id: str
    timestamp: str
    action: str
    confidence: int
    source: str

