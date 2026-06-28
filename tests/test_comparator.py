import pytest
from datetime import date

from app.models.enums import IssueCode, JobIssueSeverity, JobItemStatus, CheckResultClass
from app.services.comparator import compare_device, Issue, ComparisonResult
from app.services.matcher import MatchResult


class TestComparator:
    def test_compare_device_no_selected(self):
        device = {
            "cell_refs": {"serial": "A1"},
            "type_norm": "TYPE",
            "serial_norm": "123",
        }
        match_result = MatchResult(
            selected=None,
            candidates_count=0,
            result_class=CheckResultClass.SUCCESS_EMPTY,
            decision_reason="Нет записей",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.SOURCE_UNCERTAIN
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.ARSHIN_NOT_FOUND
        assert result.issues[0].severity == JobIssueSeverity.YELLOW

    def test_compare_device_ambiguous(self):
        device = {
            "cell_refs": {"serial": "A1"},
            "type_norm": "TYPE",
            "serial_norm": "123",
        }
        match_result = MatchResult(
            selected={"mi_number": "123", "mi_type": "TYPE"},
            candidates_count=2,
            result_class=CheckResultClass.AMBIGUOUS_MULTIPLE_MATCHES,
            decision_reason="Разные типы",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.AMBIGUOUS
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.MULTIPLE_MATCHES
        assert result.issues[0].severity == JobIssueSeverity.ORANGE

    def test_compare_device_match(self):
        device = {
            "cell_refs": {"type": "B1", "serial": "B2", "verification_date": "B3", "next_date": "B4", "link": "B5"},
            "type_norm": "TYPE",
            "serial_norm": "123",
            "verification_date_norm": date(2022, 1, 1),
            "next_date_norm": date(2022, 12, 31),
            "link_vri": "2-12345",
        }
        match_result = MatchResult(
            selected={
                "mi_number": "123",
                "mi_type": "TYPE",
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
                "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/2-12345",
            },
            candidates_count=1,
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason="Лучший кандидат",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.MATCHED
        # Должен быть один issue с кодом MATCH
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.MATCH
        assert result.issues[0].severity == JobIssueSeverity.INFO

    def test_compare_device_type_mismatch(self):
        device = {
            "cell_refs": {"type": "C1"},
            "type_norm": "TYPE_A",
            "serial_norm": "123",
            "verification_date_norm": date(2022, 1, 1),
            "next_date_norm": date(2022, 12, 31),
            "link_vri": "2-12345",
        }
        match_result = MatchResult(
            selected={
                "mi_number": "123",
                "mi_type": "TYPE_B",
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
                "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/2-12345",
            },
            candidates_count=1,
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason="Лучший кандидат",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.MISMATCH
        assert any(issue.code == IssueCode.TYPE_MISMATCH for issue in result.issues)

    def test_compare_device_date_mismatch(self):
        device = {
            "cell_refs": {"verification_date": "D1"},
            "type_norm": "TYPE",
            "serial_norm": "123",
            "verification_date_norm": date(2022, 1, 1),
            "next_date_norm": date(2022, 12, 31),
            "link_vri": "2-12345",
        }
        match_result = MatchResult(
            selected={
                "mi_number": "123",
                "mi_type": "TYPE",
                "verification_date": date(2023, 1, 1),  # отличается
                "valid_date": date(2023, 12, 31),
                "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/2-12345",
            },
            candidates_count=1,
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason="Лучший кандидат",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.MISMATCH
        assert any(issue.code == IssueCode.VERIFICATION_DATE_MISMATCH for issue in result.issues)

    def test_compare_device_placeholder_date(self):
        device = {
            "cell_refs": {"verification_date": "E1"},
            "type_norm": "TYPE",
            "serial_norm": "123",
            "verification_date_norm": "INVALID",
            "next_date_norm": date(2022, 12, 31),
            "link_vri": "2-12345",
        }
        match_result = MatchResult(
            selected={
                "mi_number": "123",
                "mi_type": "TYPE",
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
                "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/2-12345",
            },
            candidates_count=1,
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason="Лучший кандидат",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.MISMATCH
        assert any(issue.code == IssueCode.PLACEHOLDER_VALUE_DETECTED for issue in result.issues)

    def test_compare_device_link_mismatch(self):
        device = {
            "cell_refs": {"link": "F1"},
            "type_norm": "TYPE",
            "serial_norm": "123",
            "verification_date_norm": date(2022, 1, 1),
            "next_date_norm": date(2022, 12, 31),
            "link_vri": "1-12345",  # отличается
        }
        match_result = MatchResult(
            selected={
                "mi_number": "123",
                "mi_type": "TYPE",
                "verification_date": date(2022, 1, 1),
                "valid_date": date(2022, 12, 31),
                "card_url": "https://fgis.gost.ru/fundmetrology/cm/results/2-12345",
            },
            candidates_count=1,
            result_class=CheckResultClass.SUCCESS_WITH_MATCH,
            decision_reason="Лучший кандидат",
        )
        result = compare_device(device, match_result)
        assert result.status == JobItemStatus.MISMATCH
        assert any(issue.code == IssueCode.LINK_MISMATCH for issue in result.issues)
