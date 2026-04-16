from fastapi import APIRouter, HTTPException

from app.services.monitoring_service import get_shipments_snapshot


router = APIRouter(tags=["shipments"])


@router.get("/shipments")
def list_shipments():
    return get_shipments_snapshot()


@router.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: str):
    shipments = get_shipments_snapshot()
    for shipment in shipments:
        if shipment.shipment_id == shipment_id:
            return shipment
    raise HTTPException(status_code=404, detail="Shipment not found")

