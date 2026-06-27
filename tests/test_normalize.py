from datetime import date, datetime, time
import pytest

from app.excel.normalize import (
    normalize_string,
    normalize_serial_for_comparison,
    normalize_serial_for_request,
    normalize_type,
    to_canonical_date,
    extract_vri_from_link,
)


class TestNormalize:
    def test_normalize_string(self):
        assert normalize_string(None) is None
        assert normalize_string("  hello  ") == "hello"
        assert normalize_string("hello\nworld") == "helloworld"
        assert normalize_string("\t\n  ") is None

    def test_normalize_serial_for_comparison(self):
        assert normalize_serial_for_comparison(None) is None
        assert normalize_serial_for_comparison("123-456") == "123456"
        assert normalize_serial_for_comparison("383938/383876") == "383938"
        assert normalize_serial_for_comparison(" 007 ") == "007"

    def test_normalize_serial_for_request(self):
        assert normalize_serial_for_request(None) is None
        assert normalize_serial_for_request("123-456") == "123-456"
        assert normalize_serial_for_request("383938/383876") == "383938/383876"
        assert normalize_serial_for_request(" 007 ") == "007"

    def test_normalize_type(self):
        assert normalize_type(None) is None
        assert normalize_type("ТЛШ-10") == "ТЛШ10"
        assert normalize_type("ТЛШ 10") == "ТЛШ10"
        assert normalize_type("  ТЛШ-10  ") == "ТЛШ10"

    def test_to_canonical_date(self):
        # None -> None
        assert to_canonical_date(None) is None
        # Пустая строка -> None
        assert to_canonical_date("") is None
        assert to_canonical_date("-") is None
        assert to_canonical_date("—") is None
        assert to_canonical_date("нет") is None
        # Заглушки
        assert to_canonical_date(0) == "INVALID"
        assert to_canonical_date(0.0) == "INVALID"
        assert to_canonical_date("31.12.1899") == "INVALID"
        assert to_canonical_date("31121899") == "INVALID"
        assert to_canonical_date(time(0, 0)) == "INVALID"
        # Корректные даты
        assert to_canonical_date("11.11.2022") == date(2022, 11, 11)
        assert to_canonical_date("11.11.22") == date(2022, 11, 11)
        assert to_canonical_date("11112022") == date(2022, 11, 11)
        assert to_canonical_date("2022-11-11") == date(2022, 11, 11)
        # datetime
        assert to_canonical_date(datetime(2022, 11, 11)) == date(2022, 11, 11)

    def test_extract_vri_from_link(self):
        assert extract_vri_from_link(None) is None
        assert extract_vri_from_link("") is None
        assert extract_vri_from_link("-") is None
        assert extract_vri_from_link("Паспорт") is None
        assert extract_vri_from_link("https://fgis.gost.ru/fundmetrology/cm/results/2-167528364") == "2-167528364"
        assert extract_vri_from_link("2-167528364") == "2-167528364"
        assert extract_vri_from_link("1-12345") == "1-12345"
