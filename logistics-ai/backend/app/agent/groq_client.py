import httpx

from app.config import GROQ_API_KEY, GROQ_MODEL


def request_llm_json(prompt: str) -> str | None:
    if not GROQ_API_KEY:
        return None

    body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a logistics action optimizer. "
                    "Return only valid JSON with keys action, confidence, reason, alert. "
                    "confidence must be an integer from 0 to 100. "
                    "reason must be a short non-empty string. "
                    "alert must be a short non-empty string."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "logistics-ai-control-tower/0.1",
        }

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    choices = payload.get("choices", [])
    if not choices:
        return None

    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str):
        return None
    return content
