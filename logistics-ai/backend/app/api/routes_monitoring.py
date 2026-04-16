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


@router.get("/monitoring/summary")
def monitoring_summary():
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


@router.post("/refresh")
def refresh_monitoring():
    invalidate_monitoring_cache()
    shipments = get_shipments_snapshot()
    cache_shipments(shipments)
    summary = get_summary(shipments)
    cache_summary(summary)
    queue_result = enqueue_refresh_job()
    return {
        "status": "refreshed",
        "shipments": len(shipments),
        "top_priority_shipment_id": shipments[0].shipment_id,
        "queued_refresh": queue_result,
    }

