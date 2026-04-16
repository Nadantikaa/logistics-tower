import logging

from celery import Celery
from redis import Redis
from redis.exceptions import RedisError

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from app.services.monitoring_service import get_shipments_snapshot


logger = logging.getLogger(__name__)

celery_app = Celery(
    "logistics_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)


def _redis_client() -> Redis:
    return Redis.from_url(CELERY_BROKER_URL, decode_responses=True)


@celery_app.task(name="evaluate_shipment_task")
def evaluate_shipment_task(shipment_id: str) -> dict:
    lock_key = f"lock:{shipment_id}"
    try:
        redis_client = _redis_client()
        lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=300)
        if not lock_acquired:
            logger.info("Skipped duplicate evaluation for shipment_id=%s", shipment_id)
            return {"status": "skipped", "reason": "lock_exists", "shipment_id": shipment_id}
    except RedisError as exc:
        logger.warning("Redis lock unavailable for shipment_id=%s: %s", shipment_id, exc)
        return {"status": "failed", "reason": "redis_unavailable", "shipment_id": shipment_id}

    try:
        # Reuse the exact Track A pipeline (ML + Groq decision path + fallback).
        shipments = get_shipments_snapshot()
        for shipment in shipments:
            if shipment.shipment_id == shipment_id:
                logger.info("Background evaluation complete for shipment_id=%s", shipment_id)
                return {
                    "status": "processed",
                    "shipment_id": shipment_id,
                    "decision": shipment.decision.model_dump() if shipment.decision else None,
                }
        logger.warning("Shipment not found during background evaluation: %s", shipment_id)
        return {"status": "not_found", "shipment_id": shipment_id}
    finally:
        try:
            redis_client.delete(lock_key)
        except RedisError:
            logger.warning("Failed to release lock for shipment_id=%s", shipment_id)
