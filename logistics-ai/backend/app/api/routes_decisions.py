import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import USE_BACKGROUND_EVALUATION
from app.models.simulation import SimulationRequest
from app.worker import evaluate_shipment_task
from app.services.monitoring_service import get_shipments_snapshot
from app.services.simulation_service import simulate_action, simulate_impact


router = APIRouter(tags=["decisions"])
logger = logging.getLogger(__name__)


@router.post("/decisions/evaluate/{shipment_id}")
def evaluate_decision(shipment_id: str):
    """
    Action Optimizer endpoint. Returns static decision with pre-computed ripple effects.
    Does NOT recompute on dropdown or refresh - provides stable baseline.
    """
    if USE_BACKGROUND_EVALUATION:
        logger.info("Triggering background evaluation for shipment_id=%s", shipment_id)
        task = evaluate_shipment_task.delay(shipment_id)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Background evaluation triggered",
                "task_id": task.id,
                "shipment_id": shipment_id,
            },
        )

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
