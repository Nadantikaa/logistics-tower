import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.config import REDIS_URL, REFRESH_QUEUE_KEY, SHIPMENTS_CACHE_TTL_SECONDS, SUMMARY_CACHE_TTL_SECONDS
from app.models.monitoring import MonitoringSummary
from app.models.shipment import Shipment


logger = logging.getLogger(__name__)

SHIPMENTS_CACHE_KEY = "cache:shipments:all"
SUMMARY_CACHE_KEY = "cache:monitoring:summary"


def get_redis_client() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=True)


def get_cached_shipments() -> list[Shipment] | None:
    try:
        payload = get_redis_client().get(SHIPMENTS_CACHE_KEY)
    except RedisError as exc:
        logger.warning("Redis GET failed for shipments cache: %s", exc)
        return None

    if not payload:
        return None

    try:
        return [Shipment.model_validate(item) for item in json.loads(payload)]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Invalid shipments cache payload, ignoring cached value: %s", exc)
        return None


def cache_shipments(shipments: list[Shipment]) -> None:
    payload = json.dumps([shipment.model_dump(mode="json") for shipment in shipments])
    try:
        get_redis_client().setex(SHIPMENTS_CACHE_KEY, SHIPMENTS_CACHE_TTL_SECONDS, payload)
    except RedisError as exc:
        logger.warning("Redis SET failed for shipments cache: %s", exc)


def get_cached_summary() -> MonitoringSummary | None:
    try:
        payload = get_redis_client().get(SUMMARY_CACHE_KEY)
    except RedisError as exc:
        logger.warning("Redis GET failed for monitoring summary cache: %s", exc)
        return None

    if not payload:
        return None

    try:
        return MonitoringSummary.model_validate(json.loads(payload))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Invalid monitoring summary cache payload, ignoring cached value: %s", exc)
        return None


def cache_summary(summary: MonitoringSummary) -> None:
    payload = json.dumps(summary.model_dump(mode="json"))
    try:
        get_redis_client().setex(SUMMARY_CACHE_KEY, SUMMARY_CACHE_TTL_SECONDS, payload)
    except RedisError as exc:
        logger.warning("Redis SET failed for monitoring summary cache: %s", exc)


def invalidate_monitoring_cache() -> None:
    try:
        get_redis_client().delete(SHIPMENTS_CACHE_KEY, SUMMARY_CACHE_KEY)
    except RedisError as exc:
        logger.warning("Redis cache invalidation failed: %s", exc)


def enqueue_refresh_job() -> dict:
    job = {
        "job_id": str(uuid4()),
        "queued_at": datetime.now(UTC).isoformat(),
        "type": "monitoring_refresh",
    }
    payload = json.dumps(job)
    try:
        redis_client = get_redis_client()
        queue_length = redis_client.rpush(REFRESH_QUEUE_KEY, payload)
    except RedisError as exc:
        logger.warning("Redis queue push failed for monitoring refresh: %s", exc)
        return {
            "status": "queue_unavailable",
            "job": job,
            "queue": REFRESH_QUEUE_KEY,
        }

    return {
        "status": "queued",
        "job": job,
        "queue": REFRESH_QUEUE_KEY,
        "queue_length": queue_length,
    }
