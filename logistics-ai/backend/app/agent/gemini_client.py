import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.config import GEMINI_API_KEY, GEMINI_MODEL


def request_gemini_json(prompt: str) -> str | None:
    if not GEMINI_API_KEY:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "action": {
                        "type": "STRING",
                        "enum": ["REROUTE", "HOLD", "SWITCH CARRIER", "EXPEDITE", "NO ACTION"],
                    },
                    "confidence": {"type": "INTEGER"},
                    "reason": {"type": "STRING"},
                    "alert": {"type": "STRING"},
                },
                "required": ["action", "confidence", "reason", "alert"],
                "propertyOrdering": ["action", "confidence", "reason", "alert"],
            },
        },
    }
    request = Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None

    candidates = payload.get("candidates", [])
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return None
    return parts[0].get("text")
