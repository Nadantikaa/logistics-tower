from fastapi import APIRouter

from app.services.monitoring_service import get_alerts, get_decision_log, get_shipments_snapshot


router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def list_alerts():
    return get_alerts(get_shipments_snapshot())


@router.get("/decision-log")
def list_decision_log():
    get_shipments_snapshot()
    return get_decision_log()

