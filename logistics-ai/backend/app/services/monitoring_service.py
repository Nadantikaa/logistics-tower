from datetime import UTC, datetime
from typing import Optional

from app.agent.decision_engine import evaluate_shipment_decision
from app.config import ALERT_CONFIDENCE_THRESHOLD
from app.ml.scoring import compute_ml_output
from app.models.alerts import AlertItem
from app.models.monitoring import DecisionLogItem, MonitoringSummary
from app.models.shipment import Shipment, ShipmentSeed, ShipmentSignal
from app.services.congestion_service import get_congestion_by_location
from app.services.news_service import get_news_by_location
from app.services.priority_service import compute_priority
from app.services.shipment_service import list_shipment_seeds
from app.services.weather_service import get_weather_signals


decision_log: list[DecisionLogItem] = []


class DecisionCacheEntry:
    def __init__(self, shipment: Shipment, timestamp: float):
        self.shipment = shipment
        self.timestamp = timestamp
        self.risk_score = shipment.ml_output.risk_score
        self.delay_probability = shipment.ml_output.delay_probability
        self.congestion_level = shipment.signals.port_congestion_level
    
    def is_expired(self, current_time: float, ttl: float = 60.0) -> bool:
        return (current_time - self.timestamp) > ttl
    
    def should_recompute(self, new_shipment: Shipment) -> bool:
        risk_delta = abs(new_shipment.ml_output.risk_score - self.risk_score)
        if risk_delta > 0.2:
            return True
        if new_shipment.ml_output.delay_probability > 0.85:
            return True
        if new_shipment.signals.port_congestion_level == "HIGH" and self.congestion_level != "HIGH":
            return True
        return False


decision_cache: dict[str, DecisionCacheEntry] = {}


def _risk_level(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    return "LOW"


def build_shipments() -> list[Shipment]:
    seeds = list_shipment_seeds()
    weather_by_location = get_weather_signals([seed.current_location for seed in seeds])
    congestion_by_location = get_congestion_by_location()
    news_by_location = get_news_by_location()
    shipments: list[Shipment] = []

    for seed in seeds:
        shipments.append(build_shipment(seed, weather_by_location, congestion_by_location, news_by_location))

    shipments.sort(key=lambda item: (item.priority, item.ml_output.risk_score), reverse=True)
    
    # Compute static ripple effects for each decision (used by Action Optimizer)
    _compute_decision_ripple_effects(shipments)
    
    return shipments


def _compute_decision_ripple_effects(shipments: list[Shipment]) -> None:
    """Compute static ripple effects for recommended actions. Called once after all shipments built."""
    from app.services.simulation_service import simulate_ripple
    
    for shipment in shipments:
        if shipment.decision:
            primary_delay, affected_ships, summary = simulate_ripple(shipment, shipments)
            shipment.decision.primary_delay_increase = primary_delay
            shipment.decision.affected_shipments_ripple = affected_ships
            shipment.decision.ripple_summary = summary


def build_shipment(
    seed: ShipmentSeed,
    weather_by_location: dict[str, dict],
    congestion_by_location: dict[str, dict],
    news_by_location: dict[str, dict],
) -> Shipment:
    import time
    current_time = time.time()
    
    # Check cache
    if seed.shipment_id in decision_cache:
        cached_entry = decision_cache[seed.shipment_id]
        if not cached_entry.is_expired(current_time):
            # Validate if recomputation is needed
            congestion_record = congestion_by_location.get(seed.current_location, {"level": "LOW"})
            ml_output = compute_ml_output(
                seed=seed,
                weather_status=weather_by_location.get(seed.current_location, {}).get("weather_status", "clear"),
                congestion_level=congestion_record["level"],
                news_tags=news_by_location.get(seed.current_location, {}).get("tags", []),
            )
            temp_shipment = Shipment(
                shipment_id=seed.shipment_id,
                origin=seed.origin,
                destination=seed.destination,
                current_location=seed.current_location,
                status=seed.status,
                priority=0,
                is_critical=seed.is_critical,
                risk_level=_risk_level(ml_output.risk_score),
                signals=ShipmentSignal(
                    weather_status=weather_by_location.get(seed.current_location, {}).get("weather_status", "clear"),
                    temperature_c=weather_by_location.get(seed.current_location, {}).get("temperature_c"),
                    port_congestion_level=congestion_record["level"],
                    news_tags=news_by_location.get(seed.current_location, {}).get("tags", []),
                    shipment_status=seed.status,
                ),
                ml_output=ml_output,
                dependent_shipments=seed.dependent_shipments,
                shared_resource=seed.shared_resource,
                execution_status=seed.execution_status,
                predicted_delay_hours=seed.predicted_delay_hours,
            )
            if not cached_entry.should_recompute(temp_shipment):
                return cached_entry.shipment
    
    congestion_record = congestion_by_location.get(seed.current_location, {"level": "LOW"})
    news_record = news_by_location.get(seed.current_location, {"tags": []})
    weather = weather_by_location.get(
        seed.current_location,
        {
            "weather_status": "clear",
            "temperature_c": None,
        },
    )
    ml_output = compute_ml_output(
        seed=seed,
        weather_status=weather["weather_status"],
        congestion_level=congestion_record["level"],
        news_tags=news_record["tags"],
    )

    priority = compute_priority(
        seed=seed,
        risk_score=ml_output.risk_score,
        delay_probability=ml_output.delay_probability,
        anomaly_score=ml_output.anomaly_score,
        congestion_level=congestion_record["level"],
    )
    if seed.is_critical:
        priority = 100

    shipment = Shipment(
        shipment_id=seed.shipment_id,
        origin=seed.origin,
        destination=seed.destination,
        current_location=seed.current_location,
        status=seed.status,
        priority=priority,
        is_critical=seed.is_critical,
        risk_level=_risk_level(ml_output.risk_score),
        signals=ShipmentSignal(
            weather_status=weather["weather_status"],
            temperature_c=weather["temperature_c"],
            port_congestion_level=congestion_record["level"],
            news_tags=news_record["tags"],
            shipment_status=seed.status,
        ),
        ml_output=ml_output,
        dependent_shipments=seed.dependent_shipments,
        shared_resource=seed.shared_resource,
        execution_status=seed.execution_status,
        predicted_delay_hours=seed.predicted_delay_hours,
    )
    shipment.decision = evaluate_shipment_decision(
        shipment,
        alternate_carrier_available=seed.alternate_carrier_available,
    )
    
    # Update cache
    decision_cache[seed.shipment_id] = DecisionCacheEntry(shipment, current_time)
    
    return shipment


def record_decisions(shipments: list[Shipment]) -> None:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    decision_log.clear()
    for shipment in shipments[:10]:
        if shipment.decision is None:
            continue
        decision_log.append(
            DecisionLogItem(
                shipment_id=shipment.shipment_id,
                timestamp=timestamp,
                action=shipment.decision.action,
                confidence=shipment.decision.confidence,
                source=shipment.decision.source,
            )
        )


def get_shipments_snapshot() -> list[Shipment]:
    shipments = build_shipments()
    record_decisions(shipments)
    return shipments


def get_summary(shipments: list[Shipment]) -> MonitoringSummary:
    top = shipments[0]
    high_risk_count = sum(1 for shipment in shipments if shipment.risk_level == "HIGH")
    summary = (
        f"{top.current_location} shipment remains the highest-risk asset due to "
        f"{top.signals.weather_status} weather and {top.signals.port_congestion_level.lower()} congestion."
    )
    return MonitoringSummary(
        top_priority_shipment_id=top.shipment_id,
        active_alerts=sum(1 for alert in get_alerts(shipments) if alert.visible),
        high_risk_shipments=high_risk_count,
        critical_summary=summary,
    )


def get_alerts(shipments: list[Shipment]) -> list[AlertItem]:
    alerts: list[AlertItem] = []
    for shipment in shipments:
        if shipment.decision is None:
            continue
        confidence = shipment.decision.confidence
        visible = confidence >= ALERT_CONFIDENCE_THRESHOLD
        severity = "info"
        if shipment.risk_level == "HIGH" and visible:
            severity = "critical"
        elif shipment.risk_level == "MEDIUM" and visible:
            severity = "warning"
        elif visible:
            severity = "info"

        alerts.append(
            AlertItem(
                shipment_id=shipment.shipment_id,
                severity=severity,
                title=f"{shipment.shipment_id} {shipment.decision.action}",
                message=shipment.decision.alert,
                confidence=confidence,
                visible=visible,
            )
        )
    return alerts


def get_decision_log() -> list[DecisionLogItem]:
    return decision_log
