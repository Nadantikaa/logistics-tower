from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_alerts import router as alerts_router
from app.api.routes_auth import router as auth_router
from app.api.routes_decisions import router as decisions_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_shipments import router as shipments_router
from app.config import ALLOWED_ORIGINS
from app.db import init_database
from app.security import require_auth


def create_app() -> FastAPI:
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
