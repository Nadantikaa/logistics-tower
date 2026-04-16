from app.services.data_store import store


def get_congestion_by_location() -> dict[str, dict]:
    items = store.read_json("congestion.json")
    return {item["location"]: item for item in items}

