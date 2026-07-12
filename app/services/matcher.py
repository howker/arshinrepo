"""Матчер: выбор записи Аршина по контракту «никогда не подставлять чужой прибор».

Контракт (согласован с заказчиком):
  1. Ровно один кандидат, чья модификация подтверждает тип из файла → SUCCESS_WITH_MATCH.
  2. Несколько кандидатов → AMBIGUOUS_MULTIPLE_MATCHES + ссылки на всех.
  3. Кандидат(ы) есть, но модификация НЕ подтверждает тип (ТШЛ vs ТЛШ) →
     AMBIGUOUS_MULTIPLE_MATCHES (показываем как сомнительного, не выдаём за найденного).
  4. Ничего не найдено → SUCCESS_EMPTY.

Регион (владелец из Excel vs org_title поверителя) — только скоринг, НЕ фильтр:
приборы бывают поверены во ВНИИФТРИ или на заводе, вне своего ЦСМ.
"""
from __future__ import annotations

import difflib
import logging
import re
from datetime import date, datetime
from typing import Any

from app.models.enums import CheckResultClass
from app.clients.arshin import ArshinSearchResult

logger = logging.getLogger(__name__)

# Порог подтверждения типа: ниже — кандидат считается сомнительным
TYPE_CONFIRM_THRESHOLD = 75.0


def fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


class MatchResult:
    """Результат выбора записи из Аршина."""
    def __init__(
        self,
        selected: dict | None = None,
        candidates_count: int = 0,
        result_class: CheckResultClass = CheckResultClass.SUCCESS_EMPTY,
        decision_reason: str = "",
        candidates: list[dict] | None = None,
    ):
        self.selected = selected
        self.candidates_count = candidates_count
        self.result_class = result_class
        self.decision_reason = decision_reason
        # Все кандидаты — нужны, чтобы показать метрологу ссылки при AMBIGUOUS
        self.candidates = candidates or []


def normalize_serial_for_gate(serial: str) -> str:
    if not serial:
        return ""
    if '/' in serial:
        serial = serial.split('/')[0]
    return re.sub(r'[\s\-_\.]', '', serial).upper()


def normalize_type_for_score(type_val: str) -> str:
    if not type_val:
        return ""
    return re.sub(r'[\s\-]', '', type_val).upper()


def model_root(value: Any) -> str:
    """Буквенный корень модели: ЗНОЛ-0.6-10 УЗ -> ЗНОЛ, ТШЛ-0,66 -> ТШЛ."""
    if not value:
        return ""
    s = re.sub(r'МОДИФИКАЦИЯ|ИСПОЛНЕНИЕ|ТИП', '', str(value).upper()).strip()
    m = re.match(r'[А-ЯA-Z]+', s)
    return m.group(0) if m else ""


EMPTY_VALUES = ('нет данных', 'нет модификации', 'нет', '-', '—', 'none', '')


def _single_field_score(file_type: str, arshin_value: Any) -> float:
    """Сходство типа из файла с одним полем Аршина."""
    if not arshin_value:
        return 0.0
    if str(arshin_value).strip().lower() in EMPTY_VALUES:
        return 0.0

    fr = model_root(file_type)
    ar = model_root(arshin_value)
    if not fr or not ar:
        return 0.0
    if fr == ar:
        return 100.0
    if fr.startswith(ar) or ar.startswith(fr):
        return 90.0
    return fuzzy_ratio(fr, ar)


def type_confirmation_score(
    file_type: str,
    arshin_modification: Any,
    arshin_mitype: Any = None,
) -> float:
    """Насколько запись Аршина подтверждает тип прибора из файла.

    Тип в Аршине может лежать в ЛЮБОМ из двух полей — единого правила нет:
      * ЗНОЛ:      mi.mitype = None,       mi.modification = "модификация ЗНОЛ.06"
      * ЕвроАЛЬФА: mi.mitype = "ЕвроАЛЬФА", mi.modification = "EA05"
    Поэтому тип считается подтверждённым, если совпал хотя бы с одним из них.

    Устойчиво к опечаткам метролога (ЗНОЛ-0.6-10 УЗ / ЗНОЛ-0.6-10-УЗ / ЗНОЛ.06),
    но НЕ путает разные модели (ТЛШ vs ТШЛ — перестановка букв).
    """
    return max(
        _single_field_score(file_type, arshin_modification),
        _single_field_score(file_type, arshin_mitype),
    )


def ensure_date(val: Any) -> date | None:
    """Безопасно конвертирует значение в date. Никогда не возвращает 'INVALID'."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val or val == "INVALID":
            return None
        # ISO 8601 из Аршина: 2023-06-12T00:00:00Z
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})T", val)
        if m:
            y, mo, d = map(int, m.groups())
            try:
                return date(y, mo, d)
            except ValueError:
                return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                pass
    return None


def is_today_in_interval(verification_date: Any, valid_date: Any) -> bool:
    vd = ensure_date(verification_date)
    valid = ensure_date(valid_date)
    if not vd or not valid:
        return False
    return vd <= datetime.now().date() <= valid


REGION_STOPWORDS = re.compile(
    r'ФБУ|ФГУП|ООО|ОАО|ЗАО|АО|ЦСМ|ФИЛИАЛ|ЦЕНТР|МЕТРОЛОГИИ|СТАНДАРТИЗАЦИИ|'
    r'ИМ\.|«|»|"|\(|\)|ГОСУДАРСТВЕННЫЙ|РЕГИОНАЛЬНЫЙ'
)


def region_tokens(value: Any) -> set[str]:
    """Значимые слова названия организации/владельца (без юр. форм)."""
    if not value:
        return set()
    s = REGION_STOPWORDS.sub(' ', str(value).upper())
    return {w for w in re.findall(r'[А-ЯA-Z]{4,}', s)}


def region_match_score(owner_context: dict | None, org_title: Any) -> float:
    """Совпадение региона владельца (из Excel) с поверителем (из Аршина).

    Только скоринг. Регион НЕ отсекает кандидатов: прибор мог быть поверен
    во ВНИИФТРИ или на заводе-изготовителе, вне своего ЦСМ.
    """
    if not owner_context or not org_title:
        return 0.0
    owner_words = set()
    for key in ('sub_company', 'object_name'):
        owner_words |= region_tokens(owner_context.get(key))
    if not owner_words:
        return 0.0

    org_words = region_tokens(org_title)
    if not org_words:
        return 0.0

    # Совпадение по корню слова (АСТРАХАНЬ / АСТРАХАНСКИЙ)
    for ow in owner_words:
        for gw in org_words:
            stem = ow[:6]
            if len(stem) >= 5 and (gw.startswith(stem) or ow.startswith(gw[:6])):
                return 100.0
    return 0.0


def select_best_match(
    item_serial_norm: str,
    item_type_norm: str | None,
    arshin_result: ArshinSearchResult,
    item_type_raw: str | None = None,
    owner_context: dict | None = None,
) -> MatchResult:
    """Выбор записи Аршина по строгому контракту."""
    records = arshin_result.records
    if not records:
        return MatchResult(
            candidates_count=0,
            result_class=arshin_result.result_class,
            decision_reason="Нет записей в Аршине",
        )

    # 1. Жёсткий серийник-гейт (ТЗ 10.1)
    gate = normalize_serial_for_gate(item_serial_norm)
    candidates = [
        r for r in records
        if normalize_serial_for_gate(r.get("mi_number", "")) == gate
    ]
    if not candidates:
        return MatchResult(
            candidates_count=len(records),
            result_class=CheckResultClass.SUCCESS_EMPTY,
            decision_reason="Нет записей с точным совпадением серийника",
        )

    file_type = item_type_raw or item_type_norm or ""

    # 2. Скоринг: подтверждение типа + регион + пригодность + актуальность
    scored: list[tuple[float, float, dict]] = []
    for rec in candidates:
        type_score = type_confirmation_score(
            file_type, rec.get("mi_modification"), rec.get("mi_type")
        )
        score = type_score
        score += region_match_score(owner_context, rec.get("org_title")) * 0.5
        if rec.get("applicability") is True:
            score += 10
        if is_today_in_interval(rec.get("verification_date"), rec.get("valid_date")):
            score += 5
        scored.append((score, type_score, rec))

    scored.sort(
        key=lambda x: (x[0], ensure_date(x[2].get("verification_date")) or date.min),
        reverse=True,
    )

    best_score, best_type_score, best_record = scored[0]
    confirmed = [s for s in scored if s[1] >= TYPE_CONFIRM_THRESHOLD]

    # 3. Ни один кандидат не подтверждает тип из файла (ТШЛ vs ТЛШ, «нет данных»).
    #    Не выдаём его за найденный — показываем как сомнительного.
    if not confirmed:
        return MatchResult(
            selected=best_record,
            candidates=[r for _, _, r in scored],
            candidates_count=len(candidates),
            result_class=CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES,
            decision_reason=(
                f"Тип в Аршине не подтверждает тип из файла "
                f"(в файле «{str(file_type).strip()}», "
                f"в Аршине «{best_record.get('mi_type') or best_record.get('mi_modification')}»). "
                f"Проверьте карточку вручную."
            ),
        )

    # 4. Ровно один подтверждённый кандидат — надёжный результат.
    if len(confirmed) == 1:
        _, _, rec = confirmed[0]
        return MatchResult(
            selected=rec,
            candidates=[rec],
            candidates_count=len(candidates),
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason=f"Единственный подтверждённый кандидат ({rec.get('mi_modification')})",
        )

    # 5. Несколько подтверждённых — пробуем разделить регионом.
    by_region = [
        s for s in confirmed
        if region_match_score(owner_context, s[2].get("org_title")) >= 100.0
    ]
    if len(by_region) == 1:
        _, _, rec = by_region[0]
        return MatchResult(
            selected=rec,
            candidates=[r for _, _, r in confirmed],
            candidates_count=len(candidates),
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason=(
                f"Выбран по совпадению региона поверителя ({rec.get('org_title')})"
            ),
        )

    # 6. Разделить невозможно — честно показываем все карточки метрологу.
    return MatchResult(
        selected=best_record,
        candidates=[r for _, _, r in confirmed],
        candidates_count=len(candidates),
        result_class=CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES,
        decision_reason=(
            f"Найдено {len(confirmed)} равнозначных записей в Аршине "
            f"с этим серийником и типом — выберите нужную вручную"
        ),
    )
