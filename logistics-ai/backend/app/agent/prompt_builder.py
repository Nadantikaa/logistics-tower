from app.models.shipment import DecisionContext


def build_decision_prompt(context: DecisionContext) -> str:
    dependent_info = ""
    if context.dependent_shipments:
        dependent_info = f"\n- dependent_shipments: {', '.join(context.dependent_shipments)}"
        if context.shared_resource:
            dependent_info += f"\n- shared_resource: {context.shared_resource}"
    
    return f"""
You are a logistics action optimization agent for a supply chain control tower.

Choose exactly one action from:
REROUTE, HOLD, SWITCH CARRIER, EXPEDITE, NO ACTION

Return only valid JSON with exactly these keys:
{{
  "action": "REROUTE | HOLD | SWITCH CARRIER | EXPEDITE | NO ACTION",
  "confidence": 0-100 integer,
  "reason": "short operational explanation",
  "alert": "short operator-facing alert"
}}

Shipment data:
- shipment_id: {context.shipment_id}
- current_location: {context.current_location}
- destination: {context.destination}
- status: {context.status}
- priority: {context.priority}
- is_critical: {str(context.is_critical).lower()}
- weather_status: {context.signals.weather_status}
- port_congestion_level: {context.signals.port_congestion_level}
- news_tags: {", ".join(context.signals.news_tags) or "none"}
- shipment_status: {context.signals.shipment_status}
- eta_prediction: {context.ml_output.eta_prediction}
- delay_probability: {context.ml_output.delay_probability}
- anomaly_score: {context.ml_output.anomaly_score}
- risk_score: {context.ml_output.risk_score}
- alternate_carrier_available: {str(context.alternate_carrier_available).lower()}{dependent_info}

Dependency Intelligence:
If dependent shipments exist, consider how your action affects downstream operations.
Prioritize actions that mitigate cascading delays.
""".strip()

