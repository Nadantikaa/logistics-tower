import json

from pydantic import ValidationError

from app.models.shipment import DecisionOutput


def parse_decision_response(raw_text: str) -> DecisionOutput:
    text = raw_text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                text = candidate
                break
            if candidate.startswith("json"):
                json_candidate = candidate[4:].strip()
                if json_candidate.startswith("{") and json_candidate.endswith("}"):
                    text = json_candidate
                    break

    payload = json.loads(text)
    payload["source"] = "llm"
    return DecisionOutput.model_validate(payload)


def can_parse_decision_response(raw_text: str) -> bool:
    try:
        parse_decision_response(raw_text)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return False
    return True

