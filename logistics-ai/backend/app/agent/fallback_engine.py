from app.models.shipment import DecisionOutput, Shipment, ActionType


def _severity_phrase(shipment: Shipment) -> str:
    return "Critical shipment" if shipment.is_critical else "Shipment"


def choose_action(shipment: Shipment, alternate_carrier_available: bool = False) -> DecisionOutput:
    risk_score = shipment.ml_output.risk_score
    delay_probability = shipment.ml_output.delay_probability
    anomaly_score = shipment.ml_output.anomaly_score
    weather = shipment.signals.weather_status
    congestion = shipment.signals.port_congestion_level
    can_switch = alternate_carrier_available and shipment.status.lower() != "delivered"

    action: ActionType
    if risk_score >= 80 and weather == "storm" and congestion == "HIGH":
        action = "REROUTE"
        confidence = 84
    elif risk_score >= 70 and anomaly_score >= 60:
        action = "HOLD"
        confidence = 78
    elif delay_probability >= 70 and can_switch:
        action = "SWITCH CARRIER"
        confidence = 76
    elif shipment.priority >= 85 and delay_probability >= 55:
        action = "EXPEDITE"
        confidence = 74
    else:
        action = "NO ACTION"
        confidence = 62

    reason = (
        f"{_severity_phrase(shipment)} at {shipment.current_location} shows {shipment.risk_level.lower()} risk "
        f"with weather='{weather}', congestion='{congestion}', and delay probability {delay_probability}%."
    )
    alert = f"{_severity_phrase(shipment)} requires attention: {action} recommended."
    return DecisionOutput(
        action=action,
        confidence=confidence,
        reason=reason,
        alert=alert,
        source="fallback",
    )
