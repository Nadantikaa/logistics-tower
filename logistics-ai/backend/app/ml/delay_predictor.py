def predict_delay_probability(
    weather_status: str,
    congestion_level: str,
    shipment_status: str,
    news_tags: list[str],
) -> int:
    weather_weight = {"clear": 5, "cloudy": 10, "rain": 18, "storm": 32}.get(weather_status, 10)
    congestion_weight = {"LOW": 8, "MEDIUM": 18, "HIGH": 30}.get(congestion_level, 10)
    status_weight = 22 if "delay" in shipment_status.lower() else 8
    news_weight = min(len(news_tags) * 6, 18)
    return max(0, min(100, weather_weight + congestion_weight + status_weight + news_weight))

