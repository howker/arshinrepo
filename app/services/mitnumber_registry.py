"""Автопостроение справочника «корень модели СИ → номера госреестра».

Зачем: серийные номера СИ в Аршине массово повторяются у совершенно разных
приборов (номер «6590» даёт 1665 записей: секундомеры, хроматографы, манометры).
Без сужения по типу правильный прибор часто вообще не попадает в выдачу.

Решение: определяем набор номеров госреестра (mi.mitnumber) для семейства модели
и фильтруем поиск по ним. Справочник строится живым запросом к Аршину при первой
встрече типа и кэшируется в БД.

ВАЖНО: это кэш НАВИГАЦИИ по реестру типов СИ, а не кэш данных о поверках.
Сведения о поверках всегда запрашиваются живьём (ТЗ: «только живые запросы»).
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.mitnumber_registry import MitnumberRegistry

logger = logging.getLogger(__name__)

# Доля от общего числа записей, ниже которой mitnumber считается шумом
MIN_SHARE = 0.01
# Максимум номеров госреестра в одном семействе
MAX_MITNUMBERS = 12
# Максимум записей, при котором корень считается слишком широким
# (например "МЕРКУРИЙ" даёт 11.5 млн — это все счётчики Меркурий всех моделей)
MAX_TOTAL_FOR_ROOT = 500_000


def model_root_variants(type_raw: str) -> list[str]:
    """Кандидаты корня модели, от узкого к широкому.

    Разделитель между буквенной и цифровой частью в реестре непредсказуем:
    "МЕРКУРИЙ 234" (пробел), "ТЛШ-10" (дефис), "ЗНОЛ.06" (точка).
    Поэтому перебираем варианты и берём первый непустой.
    """
    if not type_raw:
        return []
    s = re.sub(r"МОДИФИКАЦИЯ|ИСПОЛНЕНИЕ|ТИП", "", str(type_raw).upper()).strip()
    m = re.match(r"[А-ЯA-Z]+", s)
    if not m:
        return []
    letters = m.group(0)
    if len(letters) < 2:
        return []
    rest = s[len(letters):]
    nums = re.findall(r"\d+", rest)

    variants: list[str] = []
    if nums:
        first = nums[0]
        variants.extend([
            f"{letters} {first}",
            f"{letters}-{first}",
            f"{letters}.{first}",
        ])
    variants.append(letters)
    return variants


class MitnumberResolver:
    """Определяет набор mi.mitnumber для типа СИ из файла."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.arshin_xcdb_url
        self.delay_ms = settings.arshin_request_delay_ms
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.arshin_timeout_read,
                                  connect=settings.arshin_timeout_connect),
            follow_redirects=True,
        )

    def _facet_mitnumbers(self, pattern: str) -> tuple[int, list[tuple[str, int]]]:
        """Facet-запрос: сколько записей у модели и какие у неё mitnumber."""
        time.sleep(self.delay_ms / 1000.0)
        q = quote(f'mi.modification:"{pattern}"')
        url = (
            f"{self.base_url}?q={q}&rows=0"
            f"&facet=true&facet.field=mi.mitnumber"
            f"&facet.limit=25&facet.mincount=1"
        )
        resp = self._client.get(url)
        if "json" not in resp.headers.get("content-type", ""):
            logger.warning("Arshin facet returned non-JSON (HTTP %s)", resp.status_code)
            return 0, []
        data = resp.json()
        total = data.get("response", {}).get("numFound", 0)
        ff = data.get("facet_counts", {}).get("facet_fields", {}).get("mi.mitnumber", [])
        pairs = [(ff[i], ff[i + 1]) for i in range(0, len(ff), 2)]
        return total, pairs

    def resolve(self, db: Session, type_raw: str) -> tuple[list[str], str] | tuple[None, str]:
        """Возвращает (mitnumbers, matched_pattern) или (None, причина)."""
        variants = model_root_variants(type_raw)
        if not variants:
            return None, "не удалось выделить корень модели"

        cache_key = variants[0]

        # 1. Кэш в БД
        cached = (
            db.query(MitnumberRegistry)
            .filter(MitnumberRegistry.model_root == cache_key)
            .first()
        )
        if cached:
            logger.debug("Mitnumber cache hit for %s", cache_key)
            return list(cached.mitnumbers), cached.matched_pattern

        # 2. Живой поиск: ОБЪЕДИНЯЕМ все варианты написания.
        # Разделитель в реестре непредсказуем ("ТЛШ 10" и "ТЛШ-10" — разные
        # непересекающиеся выборки), поэтому брать первый непустой нельзя:
        # так теряется больше половины реальных приборов семейства.
        merged: dict[str, int] = {}
        grand_total = 0
        used_patterns: list[str] = []

        for pattern in variants:
            try:
                total, pairs = self._facet_mitnumbers(pattern)
            except Exception as e:
                logger.warning("Facet request failed for %r: %s", pattern, e)
                continue

            if not total or not pairs:
                continue
            if total > MAX_TOTAL_FOR_ROOT:
                # Корень слишком широкий (например "МЕРКУРИЙ" = все модели Меркурий,
                # 11.5 млн записей). Такой вариант игнорируем.
                logger.info("Pattern %r too broad (%s records), skipped", pattern, total)
                continue

            used_patterns.append(pattern)
            grand_total += total
            for mitn, cnt in pairs:
                merged[mitn] = merged.get(mitn, 0) + cnt

        if not merged:
            return None, f"семейство не найдено в Аршине (пробовали: {variants})"

        ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)
        mitnumbers = [
            m for m, cnt in ranked[:MAX_MITNUMBERS]
            if cnt / grand_total >= MIN_SHARE
        ]
        if not mitnumbers:
            mitnumbers = [ranked[0][0]]

        matched_pattern = " | ".join(used_patterns)
        entry = MitnumberRegistry(
            model_root=cache_key,
            matched_pattern=matched_pattern[:255],
            mitnumbers=mitnumbers,
            total_found=grand_total,
        )
        db.add(entry)
        db.commit()
        logger.info(
            "Built mitnumber family for %r via [%s]: %s (%s records)",
            cache_key, matched_pattern, mitnumbers, grand_total,
        )
        return mitnumbers, matched_pattern


mitnumber_resolver = MitnumberResolver()
