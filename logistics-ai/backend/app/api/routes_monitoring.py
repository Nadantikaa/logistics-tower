import logging

from fastapi import APIRouter

from app.services.monitoring_service import get_shipments_snapshot, get_summary
from app.services.redis_service import (
    cache_shipments,
    cache_summary,
    enqueue_refresh_job,
    get_cached_shipments,
    get_cached_summary,
    invalidate_monitoring_cache,
)


router = APIRouter(tags=["monitoring"])
logger = logging.getLogger(__name__)


@router.get("/monitoring/summary")
def monitoring_summary():
<<<<<<< HEAD
    shipments = get_shipments_snapshot()
    logger.info("monitoring.summary_generated", extra={"shipment_count": len(shipments)})
    return get_summary(shipments)
=======
    cached_summary = get_cached_summary()
    if cached_summary is not None:
        return cached_summary

    shipments = get_cached_shipments()
    if shipments is None:
        shipments = get_shipments_snapshot()
        cache_shipments(shipments)

    summary = get_summary(shipments)
    cache_summary(summary)
    return summary
>>>>>>> jeff


@router.post("/refresh")
def refresh_monitoring():
    invalidate_monitoring_cache()
    shipments = get_shipments_snapshot()
<<<<<<< HEAD
    logger.info(
        "monitoring.refreshed",
        extra={
            "shipment_count": len(shipments),
            "shipment_id": shipments[0].shipment_id if shipments else None,
        },
    )
=======
    cache_shipments(shipments)
    summary = get_summary(shipments)
    cache_summary(summary)
    queue_result = enqueue_refresh_job()
>>>>>>> jeff
    return {
        "status": "refreshed",
        "shipments": len(shipments),
        "top_priority_shipment_id": shipments[0].shipment_id,
        "queued_refresh": queue_result,
    }

