from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.schemas.arshin import ArshinRecordDTO

logger = logging.getLogger(__name__)


class ArshinRateLimitError(RuntimeError):
    pass


class ArshinUpstreamUnavailableError(RuntimeError):
    pass


def _is_retryable_arshin_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        if exc.response.status_code in {500, 502, 503, 504}:
            return True
    return False


def _parse_ru_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError:
        return None


class ArshinClientAdapter:
    def __init__(
        self,
        base_url: str,
        timeout_connect: float,
        timeout_read: float,
        max_retries: int,
        backoff_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_read, connect=timeout_connect)
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        last_status_code: int | None = None
        last_body: str | None = None

        try:
            for attempt in Retrying(
                retry=retry_if_exception(_is_retryable_arshin_error),
                wait=wait_exponential(
                    multiplier=self.backoff_seconds,
                    min=self.backoff_seconds,
                    max=30,
                ),
                stop=stop_after_attempt(self.max_retries),
                reraise=True,
            ):
                with attempt:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(self.base_url, params=params)
                        response.raise_for_status()
                        return response.json()
            return {}
        except httpx.HTTPStatusError as exc:
            last_status_code = exc.response.status_code
            last_body = exc.response.text
            if last_status_code == 429:
                raise ArshinRateLimitError("Arshin API rate limit reached") from exc
            if last_status_code in {500, 502, 503, 504}:
                raise ArshinUpstreamUnavailableError(
                    f"Arshin upstream unavailable: HTTP {last_status_code}"
                ) from exc
            raise
        except Exception:
            logger.exception(
                "Arshin API request failed",
                extra={"params": params, "status_code": last_status_code, "body": last_body},
            )
            raise

    def search_device(self, type_val: str, serial_number: str) -> list[ArshinRecordDTO]:
        if not type_val or not serial_number:
            return []

        params = {
            "search": f"{type_val} {serial_number}",
            "start": 0,
            "rows": 10,
        }

        try:
            data = self._request(params)
            return self._parse_arshin_response(data)
        except ArshinRateLimitError:
            raise
        except ArshinUpstreamUnavailableError:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            logger.error(
                "Arshin API HTTP error",
                extra={"status_code": exc.response.status_code, "body": exc.response.text},
            )
            raise
        except Exception:
            logger.exception("Arshin API request failed", extra={"params": params})
            raise

    def _parse_arshin_response(self, raw_data: dict[str, Any]) -> list[ArshinRecordDTO]:
        results: list[ArshinRecordDTO] = []
        items = raw_data.get("result", {}).get("items") or raw_data.get("items") or []

        for item in items:
            try:
                vri_id = str(item.get("vri_id") or item.get("vriId") or "")
                if not vri_id:
                    continue

                results.append(
                    ArshinRecordDTO(
                        vri_id=vri_id,
                        mi_mitnumber=item.get("mit_number") or item.get("mi", {}).get("mit_number"),
                        mi_title=item.get("mit_title") or item.get("mi", {}).get("mit_title"),
                        mi_number=item.get("mi_number") or item.get("mi", {}).get("number"),
                        verification_date=_parse_ru_date(item.get("verification_date")),
                        valid_date=_parse_ru_date(item.get("valid_date")),
                        is_valid=bool(item.get("applicability", True)),
                        public_url=f"https://fgis.gost.ru/fundmetrology/cm/results/{vri_id}",
                    )
                )
            except Exception:
                logger.exception("Failed to parse Arshin item", extra={"item": item})

        return results


settings = get_settings()

arshin_client = ArshinClientAdapter(
    base_url=settings.arshin_base_url,
    timeout_connect=settings.arshin_timeout_connect,
    timeout_read=settings.arshin_timeout_read or settings.arshin_timeout_seconds,
    max_retries=settings.arshin_max_retries,
    backoff_seconds=settings.arshin_backoff_seconds,
)
