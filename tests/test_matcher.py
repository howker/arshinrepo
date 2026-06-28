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

    def test_select_best_match_ambiguous(self):
        # Две записи с одинаковым серийником, но разными типами
        records = [
            {
                "mi_number": "123-456",
                "mi_type": "TYPE_A",
                "applicability": True,
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
            },
            {
                "mi_number": "123-456",
                "mi_type": "TYPE_B",
                "applicability": True,
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
            },
        ]
        arshin_result = ArshinSearchResult(records=records, result_class=CheckResultClass.SUCCESS_WITH_MATCH)
        result = select_best_match("123-456", "TYPE_A", arshin_result)
        # Должен быть AMBIGUOUS_MULTIPLE_MATCHES, так как типы разные
        assert result.result_class == CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES
        assert "Разные типы" in result.decision_reason
