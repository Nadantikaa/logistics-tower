import json
import logging
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.config import OPENWEATHER_API_KEY, OPENWEATHER_COUNTRY, OPENWEATHER_UNITS


logger = logging.getLogger(__name__)

LOCATION_QUERY_MAP = {
    "Chennai Port": {"q": f"Chennai,{OPENWEATHER_COUNTRY}"},
    "Mumbai Port": {"q": f"Mumbai,{OPENWEATHER_COUNTRY}"},
    "Visakhapatnam Port": {"q": f"Visakhapatnam,{OPENWEATHER_COUNTRY}"},
    "Kolkata Port": {"q": f"Kolkata,{OPENWEATHER_COUNTRY}"},
}


def map_weather_condition(condition: str) -> str:
    if condition == "Thunderstorm":
        return "storm"
    if condition == "Rain":
        return "rain"
    if condition == "Clouds":
        return "cloudy"
    if condition == "Clear":
        return "clear"
    return "clear"


def _fallback_weather(location: str, source: str = "fallback") -> dict:
    return {
        "location": location,
        "weather_status": "clear",
        "temperature_c": None,
        "source": source,
        "stale": True,
    }


def _demo_override_weather(location: str) -> dict:
    return {
        "location": location,
        "weather_status": "storm",
        "temperature_c": 30.0,
        "source": "demo_override",
        "stale": False,
    }


def get_weather_signal_for_location(location: str) -> dict:
    if location == "Chennai Port":
        return _demo_override_weather(location)

    if not OPENWEATHER_API_KEY:
        logger.warning("OpenWeather API key missing; defaulting weather to clear for %s", location)
        return _fallback_weather(location)

    query_config = LOCATION_QUERY_MAP.get(location)
    if query_config is None:
        logger.warning("No weather lookup mapping configured for %s; defaulting to clear", location)
        return _fallback_weather(location, source="mapping_fallback")

    query = urlencode(
        {
            **query_config,
            "appid": OPENWEATHER_API_KEY,
            "units": OPENWEATHER_UNITS,
        }
    )
    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"

    # Retry logic with exponential backoff
    max_retries = 2
    timeout = 10  # Increased from 5 to 10 seconds
    
    for attempt in range(max_retries):
        try:
            with urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            
            condition = payload["weather"][0]["main"]
            return {
                "location": location,
                "weather_status": map_weather_condition(condition),
                "temperature_c": payload["main"].get("temp"),
                "source": "openweather",
                "stale": False,
            }
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s backoff
                logger.debug("OpenWeather lookup failed for %s (attempt %d); retrying in %ds. Error: %s", location, attempt + 1, wait_time, exc)
                time.sleep(wait_time)
            else:
                logger.warning("OpenWeather lookup failed for %s after %d attempts; defaulting to clear. Error: %s", location, max_retries, exc)
                return _fallback_weather(location)
    
    return _fallback_weather(location)


def get_weather_signals(locations: list[str]) -> dict[str, dict]:
    return {location: get_weather_signal_for_location(location) for location in locations}
