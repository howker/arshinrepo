"""Клиент для работы с API ФГИС «Аршин» (ТЗ раздел 9)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.models.enums import CheckResultClass
from app.excel.normalize import to_canonical_date

logger = logging.getLogger(__name__)


class ArshinRateLimitError(RuntimeError):
    pass


class ArshinUpstreamUnavailableError(RuntimeError):
    pass


class ArshinSearchResult:
    """Результат поиска (ТЗ 9.1) с полями для аудита (ТЗ 4.7)."""
    def __init__(
        self,
        records: list[dict],
        raw_response: dict | None = None,
        result_class: CheckResultClass = CheckResultClass.SUCCESS_EMPTY,
        candidates_count: int = 0,
        request_url: str | None = None,
        request_params: dict | None = None,
        http_status: int | None = None,
        response_time_ms: int | None = None,
        transport_error: str | None = None,
        attempts: int = 1,
    ):
        self.records = records
        self.raw_response = raw_response or {}
        self.result_class = result_class
        self.candidates_count = candidates_count
        self.request_url = request_url
        self.request_params = request_params
        self.http_status = http_status
        self.response_time_ms = response_time_ms
        self.transport_error = transport_error
        self.attempts = attempts


def _is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in {429, 500, 502, 503, 504}:
            return True
    return False


# Пауза после 429 (Too Many Requests). Аршин — общедоступный государственный
# ресурс с ограниченной пропускной способностью; при троттлинге корректнее
# подождать подольше, чем продолжать давить запросами.
RATE_LIMIT_COOLDOWN_SECONDS = 60.0
MAX_COOLDOWN_SECONDS = 300.0


def _cooldown_after_rate_limit(response: httpx.Response | None) -> float:
    """Сколько ждать после 429: уважаем Retry-After, если он есть."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), MAX_COOLDOWN_SECONDS)
            except ValueError:
                pass
    return RATE_LIMIT_COOLDOWN_SECONDS


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

    def _build_xcdb_url_with_family(
        self, serial: str, fields: list[str], mitnumbers: list[str]
    ) -> str:
        """URL с фильтром по номерам госреестра (ТЗ 10.1, сужение выдачи).

        Без этого фильтра короткий серийник (например "6590") даёт 1600+ записей
        совершенно разных приборов, и нужный прибор может вообще не попасть
        в первые rows=100. С фильтром выдача схлопывается до единиц.
        """
        from urllib.parse import quote
        fl = ",".join(fields)
        mitn_or = " OR ".join(f'"{m}"' for m in mitnumbers)
        fq_family = quote(f"mi.mitnumber:({mitn_or})")
        return (
            f"{self.xcdb_url}?q=*"
            f"&fq=mi.number:\"{serial}\""
            f"&fq={fq_family}"
            f"&fl={fl}&rows={self.rows}&start=0"
        )

    def _build_eapi_url(self, serial: str) -> str:
        return f"{self.eapi_url}?search={serial}&rows={self.rows}"

    def _parse_xcdb_response(self, data: dict) -> list[dict]:
        return data.get("response", {}).get("docs", [])

    def _parse_eapi_response(self, data: dict) -> list[dict]:
        return data.get("items", [])

    def _map_field(self, record: dict, field_map: dict) -> dict:
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
        if mode == "xcdb":
            field_map = {
                "vri_id": "vri_id",
                "mi_number": "mi.number",
                "mi_mitnumber": "mi.mitnumber",
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
        result = {}
        for k, v in raw.items():
            if v is None:
                continue
            if isinstance(v, str):
                v = v.strip()
            if k in {"verification_date", "valid_date"}:
                v = to_canonical_date(v)
            result[k] = v
        if result.get("vri_id"):
            result["card_url"] = f"{self.card_url}/{result['vri_id']}"
        return result

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        reraise=True,
    )
    def _make_request(self, url: str, serial: str, attempt: int = 1) -> dict:
        """Выполнение запроса с ретраями (ТЗ 9.3), возвращает словарь с деталями."""
        self._throttle()
        start_time = time.time()
        result = {
            "url": url,
            "params": {},
            "http_status": None,
            "response_time_ms": None,
            "transport_error": None,
            "data": None,
        }
        try:
            resp = self._client.get(url)
            elapsed = (time.time() - start_time) * 1000
            result["response_time_ms"] = elapsed
            result["http_status"] = resp.status_code
            resp.raise_for_status()
            result["data"] = resp.json()
            return result
        except httpx.HTTPStatusError as e:
            elapsed = (time.time() - start_time) * 1000
            result["response_time_ms"] = elapsed
            result["transport_error"] = str(e)
            if e.response.status_code == 429:
                cooldown = _cooldown_after_rate_limit(e.response)
                logger.warning(
                    "Arshin rate limit (429). Пауза %.0f с перед повтором.",
                    cooldown, extra={"serial": serial},
                )
                time.sleep(cooldown)
            else:
                logger.warning(
                    "Arshin request failed (attempt %s): %s",
                    attempt, str(e), extra={"serial": serial, "url": url}
                )
            raise
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            result["response_time_ms"] = elapsed
            result["transport_error"] = str(e)
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
        mitnumbers: list[str] | None = None,
    ) -> ArshinSearchResult:
        """Поиск по точному серийнику (ТЗ 9.1).

        Если передан mitnumbers (номера госреестра семейства модели), выдача
        дополнительно сужается фильтром по ним. Это критично: короткий серийник
        без такого фильтра возвращает тысячи записей чужих приборов, и нужный
        прибор может не попасть в rows=100 вообще.
        """
        # Проверка кэша (ТЗ 9.4)
        fam_key = ",".join(sorted(mitnumbers)) if mitnumbers else ""
        cache_key = f"{serial_norm}:{type_norm or ''}:{fam_key}"
        if cache_key in self._cache:
            logger.debug("Cache hit for %s", cache_key)
            return self._cache[cache_key]

        mode = self.api_mode
        fields = [
            "vri_id", "mi.number", "mi.mitnumber", "mi.mitype", "mi.mititle",
            "mi.modification", "verification_date", "valid_date",
            "applicability", "org_title"
        ] if mode == "xcdb" else [
            "vri_id", "mi_number", "mi_mitype", "mit_title",
            "mi_modification", "verification_date", "valid_date",
            "applicability", "org_title"
        ]

        if mode == "xcdb":
            if mitnumbers:
                url = self._build_xcdb_url_with_family(serial_norm, fields, mitnumbers)
            else:
                url = self._build_xcdb_url(serial_norm, fields)
            parse_func = self._parse_xcdb_response
        else:
            url = self._build_eapi_url(serial_norm)
            parse_func = self._parse_eapi_response
            if self.year_sweep:
                # Упрощённо: можно добавить перебор по годам, но пропустим
                pass

        # Выполнение запроса с ретраями
        last_error = None
        req_result = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req_result = self._make_request(url, serial_norm, attempt)
                data = req_result["data"]
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
            if type_norm:
                alt_url = self._build_eapi_url(f"{type_norm} {serial_norm}")
                try:
                    req_result_alt = self._make_request(alt_url, serial_norm, 1)
                    records_raw = parse_func(req_result_alt["data"])
                    # Если альтернативный запрос сработал, используем его результат для аудита
                    if records_raw and req_result_alt:
                        req_result = req_result_alt
                except Exception:
                    pass

        records = [self._normalize_candidate(r, mode) for r in records_raw]

        if records:
            result_class = CheckResultClass.SUCCESS_WITH_MATCH
        else:
            result_class = CheckResultClass.SUCCESS_EMPTY

        # Формируем результат с аудит-полями
        result = ArshinSearchResult(
            records=records,
            raw_response=data,
            result_class=result_class,
            candidates_count=len(records),
            request_url=req_result.get("url") if req_result else None,
            request_params=req_result.get("params") if req_result else None,
            http_status=req_result.get("http_status") if req_result else None,
            response_time_ms=req_result.get("response_time_ms") if req_result else None,
            transport_error=req_result.get("transport_error") if req_result else None,
            attempts=self.max_retries,
        )

        self._cache[cache_key] = result
        return result

    def clear_cache(self):
        """Очистка кэша (по окончании job)."""
        self._cache.clear()

    def close(self):
        self._client.close()


# Глобальный экземпляр (singleton)
arshin_client = ArshinClient()
