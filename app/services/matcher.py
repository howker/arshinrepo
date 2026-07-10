"""Матчер: серийник-гейт + score-выбор (ТЗ раздел 10)."""
from __future__ import annotations

import difflib
import logging
import re
from datetime import date, datetime
from typing import Any

from app.models.enums import CheckResultClass
from app.clients.arshin import ArshinSearchResult

logger = logging.getLogger(__name__)


def fuzzy_ratio(a: str, b: str) -> float:
    """Простая нечёткая оценка схожести (без external зависимостей)."""
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a, b)
    return seq.ratio() * 100


class MatchResult:
    """Результат выбора записи из Аршина."""
    def __init__(
        self,
        selected: dict | None = None,
        candidates_count: int = 0,
        result_class: CheckResultClass = CheckResultClass.SUCCESS_EMPTY,
        decision_reason: str = "",
    ):
        self.selected = selected
        self.candidates_count = candidates_count
        self.result_class = result_class
        self.decision_reason = decision_reason


def normalize_serial_for_gate(serial: str) -> str:
    """Нормализация для жёсткого сравнения (ТЗ 8.1, 10.1)."""
    if not serial:
        return ""
    if '/' in serial:
        serial = serial.split('/')[0]
    return re.sub(r'[\s\-_\.]', '', serial).upper()


def normalize_type_for_score(type_val: str) -> str:
    """Нормализация типа для сравнения (ТЗ 10.2)."""
    if not type_val:
        return ""
    return re.sub(r'[\s\-]', '', type_val).upper()


def ensure_date(val: Any) -> date | None:
    """Безопасно конвертирует строку в date, если это возможно."""
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                pass
    return None


def is_today_in_interval(verification_date: Any, valid_date: Any) -> bool:
    """Проверяет, покрывает ли интервал сегодняшний день."""
    vd = ensure_date(verification_date)
    valid = ensure_date(valid_date)
    if not vd or not valid:
        return False
    today = datetime.now().date()
    return vd <= today <= valid


def select_best_match(
    item_serial_norm: str,
    item_type_norm: str | None,
    arshin_result: ArshinSearchResult,
) -> MatchResult:
    """Выбор лучшей записи по ТЗ раздел 10."""
    records = arshin_result.records
    if not records:
        return MatchResult(
            candidates_count=0,
            result_class=arshin_result.result_class,
            decision_reason="Нет записей в Аршине",
        )

    # 1. Жёсткий серийник-гейт
    gate_serial = normalize_serial_for_gate(item_serial_norm)
    candidates = []
    for rec in records:
        rec_serial = normalize_serial_for_gate(rec.get("mi_number", ""))
        if rec_serial == gate_serial:
            candidates.append(rec)

    if not candidates:
        logger.info("No candidates after serial gate for %s", item_serial_norm)
        return MatchResult(
            candidates_count=len(records),
            result_class=CheckResultClass.SUCCESS_EMPTY,
            decision_reason="Нет записей с точным совпадением серийника",
        )

    # 2. Score внутри серийник-точных
    scored = []
    for rec in candidates:
        score = 0
        rec_type_norm = normalize_type_for_score(rec.get("mi_type", ""))
        if item_type_norm and rec_type_norm:
            if rec_type_norm == normalize_type_for_score(item_type_norm):
                score += 70
            else:
                ratio = fuzzy_ratio(rec_type_norm, normalize_type_for_score(item_type_norm))
                if ratio >= 85:
                    score += 35

        if rec.get("applicability") is True:
            score += 30

        vd = rec.get("verification_date")
        valid = rec.get("valid_date")
        if vd and valid:
            if is_today_in_interval(vd, valid):
                score += 10
        scored.append((score, rec))

    # Сортировка по score (убывание), затем по verification_date (защита от строк)
    scored.sort(key=lambda x: (
        x[0],
        ensure_date(x[1].get("verification_date")) or date.min
    ), reverse=True)

    best_score, best_record = scored[0]

    # Проверка на неоднозначность
    if len(scored) > 1:
        second_score = scored[1][0]
        if best_score - second_score < 30:
            return MatchResult(
                selected=best_record,
                candidates_count=len(candidates),
                result_class=CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES,
                decision_reason=f"Неоднозначный выбор: разрыв score {best_score - second_score}",
            )
        
        best_type = normalize_type_for_score(best_record.get("mi_type", ""))
        second_type = normalize_type_for_score(scored[1][1].get("mi_type", ""))
        if best_type and second_type and best_type != second_type:
            return MatchResult(
                selected=best_record,
                candidates_count=len(candidates),
                result_class=CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES,
                decision_reason="Разные типы СИ на один серийник",
            )

    return MatchResult(
        selected=best_record,
        candidates_count=len(candidates),
        result_class=CheckResultClass.SUCCESS_WITH_MATCH,
        decision_reason=f"Выбран лучший кандидат (score={best_score})",
    )
