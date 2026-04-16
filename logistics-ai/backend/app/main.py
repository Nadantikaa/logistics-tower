import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_alerts import router as alerts_router
from app.api.routes_auth import router as auth_router
from app.api.routes_decisions import router as decisions_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_shipments import router as shipments_router
from app.config import ALLOWED_ORIGINS, LOG_FILE_PATH, LOG_LEVEL, LOG_SERVICE_NAME
from app.db import init_database
from app.logging_config import clear_request_context, configure_logging, set_request_context
from app.security import require_auth


logger = logging.getLogger("app.request")


def create_app() -> FastAPI:
    configure_logging(
        log_level=LOG_LEVEL,
        service_name=LOG_SERVICE_NAME,
        log_file_path=LOG_FILE_PATH,
    )
    init_database()
    app = FastAPI(
        title="Logistics AI Control Tower",
        version="0.1.0",
        description="Backend for shipment monitoring and decision support.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS or ["http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def structured_request_logging(request: Request, call_next):
        started_at = time.perf_counter()
        request_id = str(uuid.uuid4())
        client_ip = request.client.host if request.client else None

        set_request_context(request_id=request_id, method=request.method)

        try:
            response = await call_next(request)
        except Exception:
            endpoint = getattr(request.scope.get("route"), "path", request.url.path)
            shipment_id = request.path_params.get("shipment_id") if request.path_params else None
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            set_request_context(
                endpoint=endpoint,
                shipment_id=shipment_id,
                status_code=500,
                duration_ms=duration_ms,
            )
            logger.exception("request.failed", extra={"client_ip": client_ip})
            clear_request_context()
            raise

        endpoint = getattr(request.scope.get("route"), "path", request.url.path)
        shipment_id = request.path_params.get("shipment_id") if request.path_params else None
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        status_code = response.status_code
        set_request_context(
            endpoint=endpoint,
            shipment_id=shipment_id,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        log_method = logger.info
        if status_code >= 500:
            log_method = logger.error
        elif status_code >= 400:
            log_method = logger.warning
        log_method("request.completed", extra={"client_ip": client_ip})
        response.headers["X-Request-ID"] = request_id
        clear_request_context()
        return response

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api")
    app.include_router(shipments_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(monitoring_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(alerts_router, prefix="/api", dependencies=[Depends(require_auth)])
    app.include_router(decisions_router, prefix="/api", dependencies=[Depends(require_auth)])
    return app


app = create_app()
