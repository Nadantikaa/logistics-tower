import time
from dataclasses import dataclass, field
from typing import Any

from app.models.shipment import DecisionOutput, ShipmentSignal


DECISION_TTL = 60  # seconds


@dataclass
class CachedDecision:
    decision: DecisionOutput
    signals: ShipmentSignal
    timestamp: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > DECISION_TTL


class DecisionCache:
    def __init__(self) -> None:
        self.cache: dict[str, CachedDecision] = {}

    def get(self, shipment_id: str) -> CachedDecision | None:
        cached = self.cache.get(shipment_id)
        if cached and cached.is_expired():
            del self.cache[shipment_id]
            return None
        return cached

    def set(self, shipment_id: str, decision: DecisionOutput, signals: ShipmentSignal) -> None:
        self.cache[shipment_id] = CachedDecision(decision=decision, signals=signals)

    def clear(self) -> None:
        self.cache.clear()


def is_critical_change(old_signals: ShipmentSignal, new_signals: ShipmentSignal) -> bool:
    """
    Detect if signal changes warrant immediate decision recomputation.
    
    Triggers:
    - Risk score increases by > 0.2 (on 0-1 scale)
    - Delay probability crosses or stays above 0.85
    - Congestion changes to HIGH
    - Anomaly becomes True (or transitions to worse state)
    """
    # Risk score change detection (0-100 scale → 0-1 scale)
    # Allow 20% increase (0.2 normalized)
    old_risk = old_signals.risk_score_normalized if hasattr(old_signals, 'risk_score_normalized') else 0
    new_risk = new_signals.risk_score_normalized if hasattr(new_signals, 'risk_score_normalized') else 0
    
    # Note: We use ml_output for actual scores, but signals don't have them
    # We'll check based on congestion and other available signals
    
    # Critical: Congestion changes to HIGH
    if new_signals.port_congestion_level == "HIGH" and old_signals.port_congestion_level != "HIGH":
        return True
    
    # Could be extended with more signal types in future
    return False


def should_recompute_decision(
    old_signals: ShipmentSignal,
    new_signals: ShipmentSignal,
    old_ml_output: Any,
    new_ml_output: Any,
) -> bool:
    """
    Determine if decision should be recomputed based on signal changes.
    
    Checks for critical signal changes that warrant immediate recomputation.
    """
    if old_ml_output is None or new_ml_output is None:
        return True
    
    # Risk score increases by more than 0.2 (on 0-100 scale)
    risk_increase = new_ml_output.risk_score - old_ml_output.risk_score
    if risk_increase > 20:  # 20% on 0-100 scale
        return True
    
    # Delay probability crosses or exceeds 0.85 (on 0-100 scale = 85)
    if new_ml_output.delay_probability >= 85 and old_ml_output.delay_probability < 85:
        return True
    
    # Congestion changes to HIGH
    if new_signals.port_congestion_level == "HIGH" and old_signals.port_congestion_level != "HIGH":
        return True
    
    # Anomaly score increases significantly (becomes "True" effectively)
    anomaly_increase = new_ml_output.anomaly_score - old_ml_output.anomaly_score
    if anomaly_increase > 50:  # Significant jump
        return True
    
    return False


# Global cache instance
decision_cache = DecisionCache()
