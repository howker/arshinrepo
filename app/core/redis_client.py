"""Единое подключение к Redis для сервисных нужд (не Celery-брокер)."""
from __future__ import annotations

import redis

from app.core.config import get_settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client
