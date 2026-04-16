def score_risk(
    delay_probability: int,
    anomaly_score: int,
    is_critical: bool,
) -> int:
    critical_weight = 12 if is_critical else 0
    return max(0, min(100, int(delay_probability * 0.55 + anomaly_score * 0.35 + critical_weight)))

