from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings


correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
job_id_ctx: ContextVar[str | None] = ContextVar("job_id", default=None)


def set_correlation_id(value: str | None) -> None:
    correlation_id_ctx.set(value)


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


def set_job_id(value: str | None) -> None:
    job_id_ctx.set(value)


def get_job_id() -> str | None:
    return job_id_ctx.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
            "job_id": get_job_id(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in ("event", "status", "user_id", "path", "method"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
