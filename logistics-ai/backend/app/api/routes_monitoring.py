from fastapi import APIRouter

from app.services.monitoring_service import get_shipments_snapshot, get_summary


router = APIRouter(tags=["monitoring"])


@router.get("/monitoring/summary")
def monitoring_summary():
    shipments = get_shipments_snapshot()
    return get_summary(shipments)


@router.post("/refresh")
def refresh_monitoring():
    shipments = get_shipments_snapshot()
    return {
        "status": "refreshed",
        "shipments": len(shipments),
        "top_priority_shipment_id": shipments[0].shipment_id,
    }

