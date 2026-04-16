from fastapi import APIRouter, HTTPException

from app.models.simulation import SimulationRequest
from app.services.monitoring_service import get_shipments_snapshot
from app.services.simulation_service import simulate_action, simulate_impact


router = APIRouter(tags=["decisions"])


@router.post("/decisions/evaluate/{shipment_id}")
def evaluate_decision(shipment_id: str):
    """
    Action Optimizer endpoint. Returns static decision with pre-computed ripple effects.
    Does NOT recompute on dropdown or refresh - provides stable baseline.
    """
    shipments = get_shipments_snapshot()
    for shipment in shipments:
        if shipment.shipment_id == shipment_id:
            return shipment.decision
    raise HTTPException(status_code=404, detail="Shipment not found")


@router.post("/simulate/impact/{shipment_id}")
def simulate_shipment_impact(shipment_id: str, payload: SimulationRequest):
    """
    What-if Analysis endpoint. Dynamically recomputes impact when user changes action.
    Returns full impact metrics and ripple effects for the selected action.
    Called ONLY in simulation mode, not in optimizer.
    """
    shipments = get_shipments_snapshot()
    for shipment in shipments:
        if shipment.shipment_id == shipment_id:
            return simulate_impact(shipment, payload.action, all_shipments=shipments)
    raise HTTPException(status_code=404, detail="Shipment not found")


@router.post("/simulate/{shipment_id}")
def simulate_shipment_action(shipment_id: str, payload: SimulationRequest):
    """Legacy simulation endpoint."""
    shipments = get_shipments_snapshot()
    for shipment in shipments:
        if shipment.shipment_id == shipment_id:
            return simulate_action(shipment, payload.action, all_shipments=shipments)
    raise HTTPException(status_code=404, detail="Shipment not found")
