import pytest
from datetime import date, datetime, timedelta

from app.services.matcher import (
    normalize_serial_for_gate,
    normalize_type_for_score,
    fuzzy_ratio,
    is_today_in_interval,
    select_best_match,
    MatchResult,
)
from app.clients.arshin import ArshinSearchResult
from app.models.enums import CheckResultClass


class TestMatcher:
    def test_normalize_serial_for_gate(self):
        assert normalize_serial_for_gate("") == ""
        assert normalize_serial_for_gate("123-456") == "123456"
        assert normalize_serial_for_gate("383938/383876") == "383938"
        assert normalize_serial_for_gate("  007  ") == "007"
        assert normalize_serial_for_gate("A-123_B") == "A123B"

    def test_normalize_type_for_score(self):
        assert normalize_type_for_score("") == ""
        assert normalize_type_for_score("ТЛШ-10") == "ТЛШ10"
        assert normalize_type_for_score("ТЛШ 10") == "ТЛШ10"
        assert normalize_type_for_score("  ТЛШ-10  ") == "ТЛШ10"

    def test_fuzzy_ratio(self):
        assert fuzzy_ratio("", "") == 0.0
        assert fuzzy_ratio("hello", "hello") == 100.0
        assert fuzzy_ratio("ТЛШ-10", "ТЛШ 10") >= 80.0
        assert fuzzy_ratio("abc", "def") < 50.0

    def test_is_today_in_interval(self):
        today = datetime.now().date()
        # Интервал, покрывающий сегодня
        assert is_today_in_interval(today - timedelta(days=1), today + timedelta(days=1)) is True
        # Интервал, не покрывающий сегодня
        assert is_today_in_interval(today - timedelta(days=10), today - timedelta(days=5)) is False
        # Пустые даты
        assert is_today_in_interval(None, today) is False
        assert is_today_in_interval(today, None) is False

    def test_select_best_match_no_records(self):
        arshin_result = ArshinSearchResult(records=[], result_class=CheckResultClass.SUCCESS_EMPTY)
        result = select_best_match("123", "TYPE", arshin_result)
        assert result.selected is None
        assert result.candidates_count == 0
        assert result.result_class == CheckResultClass.SUCCESS_EMPTY
        assert "Нет записей в Аршине" in result.decision_reason

    def test_select_best_match_serial_gate(self):
        # Создаём записи: одна с совпадающим серийником, другая с другим
        records = [
            {
                "mi_number": "123-456",
                "mi_type": "TYPE_A",
                "applicability": True,
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
            },
            {
                "mi_number": "789-012",
                "mi_type": "TYPE_B",
                "applicability": True,
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
            },
        ]
        arshin_result = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match("123-456", "TYPE_A", arshin_result)
        assert result.selected is not None
        assert result.selected["mi_number"] == "123-456"
        assert result.candidates_count == 1
        assert result.result_class == CheckResultClass.SUCCESS_WITH_MATCH

    def _rec(self, **kw):
        base = {
            "mi_number": "6590",
            "mi_modification": None,
            "mi_type": None,
            "applicability": True,
            "verification_date": date(2023, 6, 12),
            "valid_date": date(2031, 6, 12),
            "org_title": "ФБУ «Курский ЦСМ»",
            "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/1-1",
        }
        base.update(kw)
        return base

    def test_foreign_device_is_not_substituted(self):
        """ТШЛ вместо ТЛШ — чужой прибор, нельзя выдавать за найденный."""
        records = [self._rec(mi_number="2301", mi_modification="ТШЛ-0,66-2 У2")]
        res = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match(
            "2301", "ТЛШ10", res, item_type_raw="ТЛШ-10",
        )
        assert result.result_class == CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES
        assert "не подтверждает" in result.decision_reason

    def test_type_confirmed_via_mitype_field(self):
        """Тип может лежать в mi_type, а не в mi_modification (ЕвроАЛЬФА/EA05)."""
        records = [self._rec(mi_number="01111479", mi_modification="EA05", mi_type="ЕвроАЛЬФА")]
        res = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match(
            "01111479", "ЕВРОАЛЬФА", res, item_type_raw="ЕвроАльфа",
        )
        assert result.result_class == CheckResultClass.SUCCESS_WITH_MATCH
        assert result.selected["vri_id"] if "vri_id" in result.selected else True

    def test_region_resolves_multiple_confirmed(self):
        """Несколько подтверждённых — выбираем по региону поверителя."""
        records = [
            self._rec(mi_modification="ЗНОЛ.06", org_title='ФБУ "ВОЛОГОДСКИЙ ЦСМ"'),
            self._rec(mi_modification="модификация ЗНОЛ.06", org_title='ФБУ "АСТРАХАНСКИЙ ЦСМ"'),
        ]
        res = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match(
            "6590", "ЗНОЛ0610УЗ", res,
            item_type_raw="ЗНОЛ-0.6-10 УЗ",
            owner_context={"sub_company": "ООО Газпром добыча Астрахань"},
        )
        assert result.result_class == CheckResultClass.SUCCESS_WITH_MATCH
        assert "АСТРАХАНСКИЙ" in result.selected["org_title"]

    def test_ambiguous_when_cannot_resolve(self):
        """Несколько подтверждённых, регион не помогает — честный AMBIGUOUS."""
        records = [
            self._rec(mi_modification="ЗНОЛ.06", org_title='ФБУ "ВОЛОГОДСКИЙ ЦСМ"'),
            self._rec(mi_modification="ЗНОЛ.06", org_title='ФБУ "КУРСКИЙ ЦСМ"'),
        ]
        res = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match(
            "6590", "ЗНОЛ0610УЗ", res,
            item_type_raw="ЗНОЛ-0.6-10 УЗ",
            owner_context={"sub_company": "ООО Газпром добыча Астрахань"},
        )
        assert result.result_class == CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES
        assert len(result.candidates) == 2

    def test_arshin_iso_dates_are_parsed(self):
        """Даты Аршина приходят в ISO-8601 и должны разбираться."""
        from app.services.matcher import ensure_date
        assert ensure_date("2023-06-12T00:00:00Z") == date(2023, 6, 12)
        assert ensure_date("INVALID") is None

    def test_model_match_distinguishes_within_family(self):
        """Сверка модели: ТЛШ-10 и ТЛШ-20 — разные приборы."""
        from app.services.matcher import model_match_score
        assert model_match_score("ТЛШ-10", "ТЛШ-20") < 85.0
        assert model_match_score("ЗНОЛ-0.6-10 УЗ", "модификация ЗНОЛ.06") >= 85.0
