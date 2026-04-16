from app.agent.fallback_engine import choose_action
from app.agent.groq_client import request_llm_json
from app.agent.prompt_builder import build_decision_prompt
from app.agent.response_parser import parse_decision_response
from app.models.shipment import DecisionContext, DecisionOutput, Shipment


def evaluate_shipment_decision(shipment: Shipment, alternate_carrier_available: bool = False) -> DecisionOutput:
    context = DecisionContext(
        shipment_id=shipment.shipment_id,
        priority=shipment.priority,
        is_critical=shipment.is_critical,
        current_location=shipment.current_location,
        destination=shipment.destination,
        status=shipment.status,
        signals=shipment.signals,
        ml_output=shipment.ml_output,
        alternate_carrier_available=alternate_carrier_available,
        dependent_shipments=shipment.dependent_shipments,
        shared_resource=shipment.shared_resource,
    )
    prompt = build_decision_prompt(context)
    raw_response = request_llm_json(prompt)
    if raw_response:
        try:
            return parse_decision_response(raw_response)
        except Exception:
            pass
    return choose_action(shipment, alternate_carrier_available=alternate_carrier_available)
