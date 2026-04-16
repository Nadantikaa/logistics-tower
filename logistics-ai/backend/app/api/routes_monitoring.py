import logging

from fastapi import APIRouter

from app.services.monitoring_service import get_shipments_snapshot, get_summary


router = APIRouter(tags=["monitoring"])
logger = logging.getLogger(__name__)


@router.get("/monitoring/summary")
def monitoring_summary():
    shipments = get_shipments_snapshot()
    logger.info("monitoring.summary_generated", extra={"shipment_count": len(shipments)})
    return get_summary(shipments)


@router.post("/refresh")
def refresh_monitoring():
    shipments = get_shipments_snapshot()
    logger.info(
        "monitoring.refreshed",
        extra={
            "shipment_count": len(shipments),
            "shipment_id": shipments[0].shipment_id if shipments else None,
        },
    )
    return {
        "status": "refreshed",
        "shipments": len(shipments),
        "top_priority_shipment_id": shipments[0].shipment_id,
    }

