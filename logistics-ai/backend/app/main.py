import logging
import logging.config
import json
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes_alerts import router as alerts_router
from app.api.routes_decisions import router as decisions_router
from app.api.routes_monitoring import router as monitoring_router
from app.api.routes_shipments import router as shipments_router
from app.api.routes_auth import router as auth_router
import logging
from logging_loki import LokiHandler

logger = logging.getLogger("myapp")

loki_handler = LokiHandler(
    url="http://loki:3100/loki/api/v1/push",
    tags={"application": "backend"},
    version="1"
)

logger.addHandler(loki_handler)
logger.setLevel(logging.INFO)

# Configure logging
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/backend.log",
            "mode": "a",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
    "loggers": {
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
os.makedirs("logs", exist_ok=True)

# Apply logging configuration
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", "unknown")
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                }
            )
            
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(process_time * 1000, 2),
                }
            )
            raise


def create_app() -> FastAPI:
    app = FastAPI(
        title="Logistics AI Control Tower",
        version="0.1.0",
        description="Day 1 backend foundation for shipment monitoring and decision support.",
    )
    
    logger.info("Initializing Logistics AI Backend")

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        logger.debug("Health check endpoint called")
        return {"status": "ok"}

    # Authentication routes (no /api prefix for auth)
    logger.info("Including authentication routes")
    app.include_router(auth_router)
    
    # API routes
    logger.info("Including API routes")
    app.include_router(shipments_router, prefix="/api")
    app.include_router(monitoring_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(decisions_router, prefix="/api")
    
    logger.info("Backend initialization complete")
    return app


app = create_app()

