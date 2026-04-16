import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.config import dictConfig
from pathlib import Path
from typing import Any


_request_context: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _request_context.get({}).items():
            if getattr(record, key, None) is None:
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    _reserved_fields = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "log_level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "endpoint": getattr(record, "endpoint", None),
            "shipment_id": getattr(record, "shipment_id", None),
            "request_id": getattr(record, "request_id", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "client_ip": getattr(record, "client_ip", None),
        }

        for key, value in record.__dict__.items():
            if key in self._reserved_fields or key in payload or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps({key: value for key, value in payload.items() if value is not None}, default=str)


def set_request_context(**values: Any) -> None:
    current = dict(_request_context.get({}))
    for key, value in values.items():
        if value is not None:
            current[key] = value
    _request_context.set(current)


def clear_request_context() -> None:
    _request_context.set({})


def configure_logging(*, log_level: str, service_name: str, log_file_path: str | None) -> None:
    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        }
    }

    if log_file_path:
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": log_file_path,
            "encoding": "utf-8",
            "formatter": "json",
            "filters": ["request_context"],
        }

    shared_handlers = list(handlers.keys())

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": "app.logging_config.RequestContextFilter",
                }
            },
            "formatters": {
                "json": {
                    "()": "app.logging_config.JsonFormatter",
                    "service_name": service_name,
                }
            },
            "handlers": handlers,
            "root": {
                "handlers": shared_handlers,
                "level": log_level.upper(),
            },
            "loggers": {
                "uvicorn": {
                    "handlers": shared_handlers,
                    "level": log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": shared_handlers,
                    "level": log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": shared_handlers,
                    "level": log_level.upper(),
                    "propagate": False,
                },
            },
        }
    )
