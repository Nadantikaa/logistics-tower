from app.models.shipment import MlOutput, ShipmentSeed
from app.ml.anomaly_detector import detect_anomaly_score
from app.ml.delay_predictor import predict_delay_probability
from app.ml.eta_predictor import predict_eta_iso
from app.ml.risk_scorer import score_risk


def compute_ml_output(
    seed: ShipmentSeed,
    weather_status: str,
    congestion_level: str,
    news_tags: list[str],
) -> MlOutput:
    delay_probability = predict_delay_probability(
        weather_status=weather_status,
        congestion_level=congestion_level,
        shipment_status=seed.status,
        news_tags=news_tags,
    )
    anomaly_score = detect_anomaly_score(
        congestion_level=congestion_level,
        news_tags=news_tags,
        is_critical=seed.is_critical,
        shipment_status=seed.status,
    )
    risk_score = score_risk(
        delay_probability=delay_probability,
        anomaly_score=anomaly_score,
        is_critical=seed.is_critical,
    )
    eta_prediction = predict_eta_iso(
        baseline_eta_hours=seed.baseline_eta_hours,
        weather_status=weather_status,
        congestion_level=congestion_level,
    )
    return MlOutput(
        eta_prediction=eta_prediction,
        delay_probability=delay_probability,
        anomaly_score=anomaly_score,
        risk_score=risk_score,
    )
