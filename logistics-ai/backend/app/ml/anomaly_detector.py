def detect_anomaly_score(
    congestion_level: str,
    news_tags: list[str],
    is_critical: bool,
    shipment_status: str,
) -> int:
    congestion_weight = {"LOW": 8, "MEDIUM": 18, "HIGH": 30}.get(congestion_level, 10)
    news_weight = min(len(news_tags) * 6, 18)
    critical_weight = 12 if is_critical else 0
    status_weight = 10 if "delay" in shipment_status.lower() else 0
    return max(0, min(100, congestion_weight + news_weight + critical_weight + status_weight))

