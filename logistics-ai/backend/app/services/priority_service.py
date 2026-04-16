from app.models.shipment import ShipmentSeed


def compute_priority(
    seed: ShipmentSeed,
    risk_score: int,
    delay_probability: int,
    anomaly_score: int,
    congestion_level: str,
) -> int:
    congestion_bonus = {"LOW": 0, "MEDIUM": 5, "HIGH": 10}[congestion_level]
    score = (
        seed.priority_base
        + int(risk_score * 0.35)
        + int(delay_probability * 0.25)
        + int(anomaly_score * 0.15)
        + congestion_bonus
    )
    return max(0, min(100, score))

