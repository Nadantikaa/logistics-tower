from datetime import UTC, datetime, timedelta


def predict_eta_iso(
    baseline_eta_hours: int,
    weather_status: str,
    congestion_level: str,
) -> str:
    eta_hours = baseline_eta_hours
    if weather_status == "storm":
        eta_hours += 3
    elif weather_status == "rain":
        eta_hours += 1

    if congestion_level == "HIGH":
        eta_hours += 2
    elif congestion_level == "MEDIUM":
        eta_hours += 1

    return (datetime.now(UTC) + timedelta(hours=eta_hours)).replace(microsecond=0).isoformat()

