import logging

from fastapi import APIRouter, HTTPException

from app.services.monitoring_service import get_shipments_snapshot
from app.services.redis_service import cache_shipments, get_cached_shipments


router = APIRouter(tags=["shipments"])
logger = logging.getLogger(__name__)


@router.get("/shipments")
def list_shipments():
<<<<<<< HEAD
    shipments = get_shipments_snapshot()
    logger.info("shipments.listed", extra={"shipment_count": len(shipments)})
=======
    cached_shipments = get_cached_shipments()
    if cached_shipments is not None:
        return cached_shipments

    shipments = get_shipments_snapshot()
    cache_shipments(shipments)
>>>>>>> jeff
    return shipments


@router.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    shipments = get_cached_shipments()
    if shipments is None:
        shipments = get_shipments_snapshot()
        cache_shipments(shipments)

    for shipment in shipments:
        if shipment.shipment_id == shipment_id:
            logger.info("shipment.fetched", extra={"shipment_id": shipment_id})
            return shipment
    logger.warning("shipment.not_found", extra={"shipment_id": shipment_id})
    raise HTTPException(status_code=404, detail="Shipment not found")

