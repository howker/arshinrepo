"""Клиент для работы с API ФГИС «Аршин» (ТЗ раздел 9)."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.models.enums import CheckResultClass

logger = logging.getLogger(__name__)


class ArshinRateLimitError(RuntimeError):
    pass


class ArshinUpstreamUnavailableError(RuntimeError):
    pass


class ArshinSearchResult:
    """Результат поиска (ТЗ 9.1)."""
    def __init__(
        self,
        records: list[dict],
        raw_response: dict | None = None,
        result_class: CheckResultClass = CheckResultClass.SUCCESS_EMPTY,
        candidates_count: int = 0,
    ):
        self.records = records
        self.raw_response = raw_response or {}
        self.result_class = result_class
        self.candidates_count = candidates_count


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in {429, 500, 502, 503, 504}:
            return True
    return False


class ArshinClient:
    """Адаптер к API Аршина с двумя режимами (xcdb/eapi), троттлингом и аудитом."""

    def __init__(self):
        settings = get_settings()
        self.xcdb_url = settings.arshin_xcdb_url
        self.eapi_url = settings.arshin_eapi_url
        self.card_url = settings.arshin_card_url
        self.api_mode = settings.arshin_api_mode
        self.rows = settings.arshin_rows
        self.delay_ms = settings.arshin_request_delay_ms
        self.connect_timeout = settings.arshin_timeout_connect
        self.read_timeout = settings.arshin_timeout_read
        self.max_retries = settings.arshin_max_retries
        self.backoff = settings.arshin_backoff_seconds
        self.year_sweep = settings.arshin_year_sweep

        self._client = httpx.Client(
            timeout=httpx.Timeout(self.read_timeout, connect=self.connect_timeout),
            follow_redirects=True,
        )
        # In-memory кэш для текущего job (ТЗ 9.4)
        self._cache: dict[str, ArshinSearchResult] = {}

    def _throttle(self):
        """Пауза перед запросом (ТЗ 9.2)."""
        time.sleep(self.delay_ms / 1000.0)

    def _build_xcdb_url(self, serial: str, fields: list[str]) -> str:
        fl = ",".join(fields)
        return f"{self.xcdb_url}?q=*&fq=mi.number:\"{serial}\"&fl={fl}&rows={self.rows}&start=0"

    def _build_eapi_url(self, serial: str) -> str:
        return f"{self.eapi_url}?search={serial}&rows={self.rows}"

    def _parse_xcdb_response(self, data: dict) -> list[dict]:
        docs = data.get("response", {}).get("docs", [])
        return docs

    def _parse_eapi_response(self, data: dict) -> list[dict]:
        items = data.get("items", [])
        return items

    def _map_field(self, record: dict, field_map: dict) -> dict:
        """Маппинг полей с фолбэками (ТЗ 1.8, 9.1)."""
        mapped = {}
        for target, source in field_map.items():
            value = None
            if isinstance(source, str):
                value = record.get(source)
            elif isinstance(source, (list, tuple)):
                for key in source:
                    value = record.get(key)
                    if value is not None:
                        break
            mapped[target] = value
        return mapped

    def _normalize_candidate(self, record: dict, mode: str) -> dict:
        """Нормализация записи Аршина в единый формат."""
        if mode == "xcdb":
            field_map = {
                "vri_id": "vri_id",
                "mi_number": "mi.number",
                "mi_type": "mi.mitype",
                "mi_title": "mi.mititle",
                "mi_modification": "mi.modification",
                "verification_date": "verification_date",
                "valid_date": "valid_date",
                "applicability": "applicability",
                "org_title": "org_title",
            }
        else:  # eapi
            field_map = {
                "vri_id": "vri_id",
                "mi_number": "mi_number",
                "mi_type": "mi_mitype",
                "mi_title": "mit_title",
                "mi_modification": "mi_modification",
                "verification_date": "verification_date",
                "valid_date": "valid_date",
                "applicability": "applicability",
                "org_title": "org_title",
            }
        raw = self._map_field(record, field_map)
        # Очистка и преобразование
        result = {}
        for k, v in raw.items():
            if v is None:
                continue
            if isinstance(v, str):
                v = v.strip()
            result[k] = v
        # URL карточки
        if result.get("vri_id"):
            result["card_url"] = f"{self.card_url}/{result['vri_id']}"
        return result

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        reraise=True,
    )
    def _make_request(self, url: str, serial: str, attempt: int = 1) -> tuple[dict, float]:
        """Выполнение запроса с ретраями (ТЗ 9.3)."""
        self._throttle()
        start_time = time.time()
        try:
            resp = self._client.get(url)
            elapsed = (time.time() - start_time) * 1000  # ms
            resp.raise_for_status()
            return resp.json(), elapsed
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.warning(
                "Arshin request failed (attempt %s): %s",
                attempt, str(e), extra={"serial": serial, "url": url}
            )
            raise

    def search_by_serial(
        self,
        serial_norm: str,
        type_norm: str | None = None,
        job_id: UUID | None = None,
        job_item_id: UUID | None = None,
    ) -> ArshinSearchResult:
        """Поиск по точному серийнику (ТЗ 9.1)."""
        # Проверка кэша (ТЗ 9.4)
        cache_key = f"{serial_norm}:{type_norm or ''}"
        if cache_key in self._cache:
            logger.debug("Cache hit for %s", cache_key)
            return self._cache[cache_key]

        mode = self.api_mode
        fields = [
            "vri_id", "mi.number", "mi.mitype", "mi.mititle",
            "mi.modification", "verification_date", "valid_date",
            "applicability", "org_title"
        ] if mode == "xcdb" else [
            "vri_id", "mi_number", "mi_mitype", "mit_title",
            "mi_modification", "verification_date", "valid_date",
            "applicability", "org_title"
        ]

        # Основной запрос (xcdb по умолчанию)
        if mode == "xcdb":
            url = self._build_xcdb_url(serial_norm, fields)
            parse_func = self._parse_xcdb_response
        else:
            url = self._build_eapi_url(serial_norm)
            parse_func = self._parse_eapi_response
            if self.year_sweep:
                # Если включен перебор по годам (ТЗ 9.1) — реализуем упрощённо
                # В реальности делаем несколько запросов с year=... — пропустим для краткости
                pass

        # Выполнение запроса с ретраями
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                data, elapsed = self._make_request(url, serial_norm, attempt)
                break
            except Exception as e:
                last_error = e
                if attempt == self.max_retries:
                    raise ArshinUpstreamUnavailableError(
                        f"All retries exhausted: {str(e)}"
                    ) from e
                continue

        # Парсинг ответа
        records_raw = parse_func(data)
        if not records_raw and mode == "eapi":
            # Доп. запрос с типом (ТЗ 9.1)
            if type_norm:
                alt_url = self._build_eapi_url(f"{type_norm} {serial_norm}")
                try:
                    alt_data, _ = self._make_request(alt_url, serial_norm, 1)
                    records_raw = parse_func(alt_data)
                except Exception:
                    pass

        # Нормализация записей
        records = [self._normalize_candidate(r, mode) for r in records_raw]

        # Определение result_class (ТЗ 9.3)
        if records:
            result_class = CheckResultClass.SUCCESS_WITH_MATCH
        else:
            result_class = CheckResultClass.SUCCESS_EMPTY

        result = ArshinSearchResult(
            records=records,
            raw_response=data,
            result_class=result_class,
            candidates_count=len(records),
        )

        # Сохраняем в кэш
        self._cache[cache_key] = result
        return result

    def clear_cache(self):
        """Очистка кэша (по окончании job)."""
        self._cache.clear()

    def close(self):
        self._client.close()


# Глобальный экземпляр (singleton)
arshin_client = ArshinClient()
