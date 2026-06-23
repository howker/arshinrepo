from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.schemas.arshin import ArshinRecordDTO

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_read, connect=timeout_connect)
        self.max_retries = max_retries

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in Retrying(
            retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(self.max_retries),
            reraise=True,
        ):
            with attempt:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(self.base_url, params=params)
                    response.raise_for_status()
                    return response.json()
        return {}

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
        items = (
            raw_data.get("result", {}).get("items")
            or raw_data.get("items")
            or []
        )

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
    timeout_read=settings.arshin_timeout_read,
    max_retries=settings.arshin_max_retries,
)
