from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ArshinRateLimitError(RuntimeError):
    """Превышен лимит запросов к Аршину (429)."""
    pass


class ArshinUpstreamUnavailableError(RuntimeError):
    """Аршин недоступен (5xx / таймаут / сеть)."""
    pass


class ArshinSearchResult:
    """Результат поиска прибора в Аршине (минимальная заглушка, полная реализация на Э4)."""

    def __init__(self, records: list[dict] | None = None, raw_response: dict | None = None):
        self.records = records or []
        self.raw_response = raw_response or {}


def _is_retryable_arshin_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        if exc.response.status_code in {500, 502, 503, 504}:
            return True
    return False


class ArshinClient:
    """Минимальная заглушка клиента Аршина (полная реализация по ТЗ §9 на Э4)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.xcdb_url = settings.arshin_xcdb_url
        self.eapi_url = settings.arshin_eapi_url
        self.api_mode = settings.arshin_api_mode
        self.timeout = httpx.Timeout(
            settings.arshin_timeout_read,
            connect=settings.arshin_timeout_connect,
        )
        self.max_retries = settings.arshin_max_retries
        self.backoff_seconds = settings.arshin_backoff_seconds

    def search_by_serial(
        self, serial_norm: str, type_norm: str | None = None
    ) -> ArshinSearchResult:
        """Заглушка: возвращает пустой результат. Полная реализация на Э4."""
        logger.warning(
            "ArshinClient.search_by_serial called (stub implementation)",
            extra={"serial": serial_norm, "type": type_norm},
        )
        return ArshinSearchResult(records=[], raw_response={})


# Глобальный экземпляр
arshin_client = ArshinClient()
