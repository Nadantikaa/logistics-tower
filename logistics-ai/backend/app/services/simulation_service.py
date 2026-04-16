from datetime import datetime, timedelta, UTC

from app.models.shipment import ActionType, Shipment
from app.models.simulation import SimulationResult, RippleEffectSummary, AffectedShipmentInfo
from app.services.ripple_engine import simulate_ripple_effect


def _parse_eta(eta_iso: str) -> datetime:
    return datetime.fromisoformat(eta_iso.replace("Z", "+00:00")).astimezone(UTC)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def simulate_ripple(shipment: Shipment, all_shipments: list[Shipment] | None = None) -> tuple[int, list[AffectedShipmentInfo], dict]:
    """Compute ripple effects only (no action deltas). Used for static baseline impact in optimizer.
    
    Returns:
    - primary_delay_increase: hours added to primary shipment
    - affected_shipments: list of downstream impacts
    - summary: dict with total_affected and max_delay
    """
    affected_shipments: list[AffectedShipmentInfo] = []
    primary_delay_increase = 0
    ripple_summary = {"total_affected": 0, "max_delay": 0}
    
    if shipment.dependent_shipments and all_shipments:
        ripple = simulate_ripple_effect(shipment, all_shipments)
        primary_delay_increase = ripple.primary_delay_increase
        affected_shipments = [
            AffectedShipmentInfo(
                id=aff.id,
                delay_increase=aff.delay_increase,
                reason=aff.reason
            )
            for aff in ripple.affected_shipments
        ]
        ripple_summary = {
            "total_affected": ripple.summary.get("total_affected", 0),
            "max_delay": ripple.summary.get("max_delay", 0)
        }
    
    return primary_delay_increase, affected_shipments, ripple_summary


def _compute_impact(shipment: Shipment, action: ActionType, all_shipments: list[Shipment] | None = None) -> SimulationResult:
    """Core impact computation logic for any action."""
    delta_map = {
        "REROUTE": {"delay": -15, "risk": -18, "hours": -2},
        "HOLD": {"delay": 10, "risk": 5, "hours": 3},
        "SWITCH CARRIER": {"delay": -10, "risk": -8, "hours": -1},
        "EXPEDITE": {"delay": -6, "risk": -5, "hours": -1},
        "NO ACTION": {"delay": 3, "risk": 2, "hours": 1},
    }
    deltas = delta_map[action].copy()
    weather = shipment.signals.weather_status
    if weather == "storm":
        deltas["delay"] += 4
        deltas["risk"] += 5
        deltas["hours"] += 1
    elif weather == "rain":
        deltas["delay"] += 2
        deltas["risk"] += 2

    baseline_eta = shipment.ml_output.eta_prediction
    simulated_eta = (_parse_eta(baseline_eta) + timedelta(hours=deltas["hours"])).replace(microsecond=0).isoformat()

    simulated_delay = _clamp(shipment.ml_output.delay_probability + deltas["delay"])
    simulated_risk = _clamp(shipment.ml_output.risk_score + deltas["risk"])
    impact_summary = (
        f"{action} changes projected delay probability from {shipment.ml_output.delay_probability}% "
        f"to {simulated_delay}% and risk from {shipment.ml_output.risk_score}% to {simulated_risk}% "
        f"under current {weather} conditions."
    )
    
    # Calculate ripple effect if dependencies exist and all_shipments provided
    affected_shipments: list[AffectedShipmentInfo] = []
    primary_delay_increase = 0
    ripple_summary = RippleEffectSummary()
    
    if shipment.dependent_shipments and all_shipments:
        ripple = simulate_ripple_effect(shipment, all_shipments)
        primary_delay_increase = ripple.primary_delay_increase
        affected_shipments = [
            AffectedShipmentInfo(
                id=aff.id,
                delay_increase=aff.delay_increase,
                reason=aff.reason
            )
            for aff in ripple.affected_shipments
        ]
        ripple_summary = RippleEffectSummary(
            total_affected=ripple.summary.get("total_affected", 0),
            max_delay=ripple.summary.get("max_delay", 0)
        )
    
    return SimulationResult(
        action=action,
        baseline_eta=baseline_eta,
        simulated_eta=simulated_eta,
        baseline_delay_probability=shipment.ml_output.delay_probability,
        simulated_delay_probability=simulated_delay,
        baseline_risk_score=shipment.ml_output.risk_score,
        simulated_risk_score=simulated_risk,
        impact_summary=impact_summary,
        primary_delay_increase=primary_delay_increase,
        affected_shipments=affected_shipments,
        ripple_summary=ripple_summary,
    )


def simulate_action(shipment: Shipment, action: ActionType, all_shipments: list[Shipment] | None = None) -> SimulationResult:
    """Legacy simulation endpoint. Use simulate_impact for dynamic what-if analysis."""
    return _compute_impact(shipment, action, all_shipments)


def simulate_impact(shipment: Shipment, action: ActionType, all_shipments: list[Shipment] | None = None) -> SimulationResult:
    """Dynamic what-if analysis. Instantly recomputes delay + downstream effects for selected action.
    
    Recomputes for all action types:
    - NO ACTION (baseline behavior)
    - REROUTE (alternative routing)
    - HOLD (delay shipment)
    - EXPEDITE (accelerate)
    - SWITCH CARRIER (change carrier)
    
    Returns immediate impact on:
    - Simulated ETA and delay probability
    - Risk score changes
    - Downstream shipment effects (ripple)
    """
    return _compute_impact(shipment, action, all_shipments)
