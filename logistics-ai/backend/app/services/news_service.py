from app.services.data_store import store


def get_news_by_location() -> dict[str, dict]:
    items = store.read_json("news.json")
    return {item["location"]: item for item in items}

