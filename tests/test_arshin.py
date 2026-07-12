import time
from datetime import date
from unittest.mock import Mock, patch

import pytest
import httpx

from app.clients.arshin import (
    ArshinClient,
    ArshinSearchResult,
    ArshinRateLimitError,
    ArshinUpstreamUnavailableError,
    CheckResultClass,
)
from app.core.config import get_settings


class TestArshinClient:
    def test_throttle(self):
        """Проверка, что _throttle делает паузу."""
        client = ArshinClient()
        start = time.time()
        client._throttle()
        elapsed = time.time() - start
        # По умолчанию delay_ms = 1000, допустим погрешность
        assert elapsed >= 0.9

    def test_build_xcdb_url(self):
        client = ArshinClient()
        fields = ["vri_id", "mi.number"]
        url = client._build_xcdb_url("12345", fields)
        assert "q=*" in url
        assert "fq=mi.number:\"12345\"" in url
        assert "fl=vri_id,mi.number" in url
        assert "rows=100" in url

    def test_build_eapi_url(self):
        client = ArshinClient()
        url = client._build_eapi_url("12345")
        assert "search=12345" in url
        assert "rows=100" in url

    def test_parse_xcdb_response(self):
        client = ArshinClient()
        data = {"response": {"docs": [{"vri_id": "1", "mi.number": "123"}]}}
        result = client._parse_xcdb_response(data)
        assert result == [{"vri_id": "1", "mi.number": "123"}]

    def test_parse_xcdb_response_empty(self):
        client = ArshinClient()
        data = {"response": {"docs": []}}
        result = client._parse_xcdb_response(data)
        assert result == []

    def test_parse_eapi_response(self):
        client = ArshinClient()
        data = {"items": [{"vri_id": "1", "mi_number": "123"}]}
        result = client._parse_eapi_response(data)
        assert result == [{"vri_id": "1", "mi_number": "123"}]

    def test_normalize_candidate_xcdb(self):
        client = ArshinClient()
        record = {
            "vri_id": "2-12345",
            "mi.number": "123/456",
            "mi.mitype": "ТЛШ-10",
            "mi.mititle": "Счётчик",
            "verification_date": "2022-01-01",
            "valid_date": "2022-12-31",
            "applicability": True,
            "org_title": "Организация",
        }
        result = client._normalize_candidate(record, "xcdb")
        assert result["vri_id"] == "2-12345"
        assert result["mi_number"] == "123/456"
        assert result["mi_type"] == "ТЛШ-10"
        assert result["verification_date"] == date(2022, 1, 1)
        assert result["valid_date"] == date(2022, 12, 31)
        assert result["card_url"] == "https://fgis.gost.ru/fundmetrology/cm/results/2-12345"

    def test_normalize_candidate_eapi(self):
        client = ArshinClient()
        record = {
            "vri_id": "1-67890",
            "mi_number": "987",
            "mi_mitype": "ТЛШ-20",
            "verification_date": "2023-01-01",
            "valid_date": "2023-12-31",
            "applicability": False,
        }
        result = client._normalize_candidate(record, "eapi")
        assert result["vri_id"] == "1-67890"
        assert result["mi_number"] == "987"
        assert result["mi_type"] == "ТЛШ-20"
        assert result["card_url"] == "https://fgis.gost.ru/fundmetrology/cm/results/1-67890"

    def test_make_request_success(self, mocker):
        """Тест успешного запроса."""
        client = ArshinClient()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": {"docs": []}}
        mocker.patch.object(client._client, "get", return_value=mock_resp)
        result = client._make_request("http://test", "123")
        assert result["http_status"] == 200
        assert result["data"] == {"response": {"docs": []}}
        assert result["transport_error"] is None

    def test_make_request_retry_on_500(self, mocker):
        """Тест ретрая при 500 ошибке."""
        client = ArshinClient()
        # Патчим _throttle, чтобы не ждать
        mocker.patch.object(client, "_throttle")
        # Мокаем get, чтобы первый раз вернуть 500, второй — 200
        mock_resp_500 = Mock()
        mock_resp_500.status_code = 500
        mock_resp_500.raise_for_status.side_effect = httpx.HTTPStatusError("", request=None, response=mock_resp_500)
        mock_resp_200 = Mock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {"ok": True}
        mock_get = mocker.patch.object(client._client, "get")
        mock_get.side_effect = [mock_resp_500, mock_resp_200]
        result = client._make_request("http://test", "123")
        assert result["http_status"] == 200
        assert result["data"] == {"ok": True}
        assert mock_get.call_count == 2

    def test_make_request_retries_exhausted(self, mocker):
        """Тест, когда все ретраи исчерпаны."""
        client = ArshinClient()
        client.max_retries = 2
        mocker.patch.object(client, "_throttle")
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("", request=None, response=mock_resp)
        mocker.patch.object(client._client, "get", return_value=mock_resp)
        with pytest.raises(httpx.HTTPStatusError):
            client._make_request("http://test", "123")

    def test_search_by_serial_xcdb_success(self, mocker):
        """Тест поиска через xcdb с успешным результатом."""
        client = ArshinClient()
        client.api_mode = "xcdb"
        # Патчим _make_request, чтобы вернуть успешный ответ с docs
        mock_response = {
            "url": "http://test",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {
                "response": {
                    "docs": [
                        {
                            "vri_id": "2-12345",
                            "mi.number": "123",
                            "mi.mitype": "TYPE",
                            "verification_date": "2022-01-01",
                            "valid_date": "2022-12-31",
                            "applicability": True,
                        }
                    ]
                }
            }
        }
        mocker.patch.object(client, "_make_request", return_value=mock_response)
        result = client.search_by_serial("123", "TYPE")
        assert isinstance(result, ArshinSearchResult)
        assert result.result_class == CheckResultClass.SUCCESS_WITH_MATCH
        assert len(result.records) == 1
        assert result.records[0]["mi_number"] == "123"
        assert result.request_url == "http://test"
        assert result.http_status == 200

    def test_search_by_serial_xcdb_empty(self, mocker):
        """Тест поиска через xcdb с пустым ответом."""
        client = ArshinClient()
        client.api_mode = "xcdb"
        mock_response = {
            "url": "http://test",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {"response": {"docs": []}}
        }
        mocker.patch.object(client, "_make_request", return_value=mock_response)
        result = client.search_by_serial("123", "TYPE")
        assert result.result_class == CheckResultClass.SUCCESS_EMPTY
        assert len(result.records) == 0

    def test_search_by_serial_cache(self, mocker):
        """Тест кэширования результатов."""
        client = ArshinClient()
        # Первый запрос — делаем реальный _make_request
        mock_response = {
            "url": "http://test",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {"response": {"docs": [{"vri_id": "1"}]}}
        }
        mock_make = mocker.patch.object(client, "_make_request", return_value=mock_response)
        result1 = client.search_by_serial("123")
        result2 = client.search_by_serial("123")
        # _make_request должен быть вызван только один раз
        assert mock_make.call_count == 1
        # Результаты должны быть одним и тем же объектом (по ссылке)
        assert result1 is result2

    def test_search_by_serial_eapi(self, mocker):
        """Тест поиска через eapi с успешным результатом."""
        client = ArshinClient()
        client.api_mode = "eapi"
        mock_response = {
            "url": "http://test",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {
                "items": [
                    {
                        "vri_id": "1-67890",
                        "mi_number": "987",
                        "mi_mitype": "TYPE",
                        "verification_date": "2023-01-01",
                        "valid_date": "2023-12-31",
                        "applicability": False,
                    }
                ]
            }
        }
        mocker.patch.object(client, "_make_request", return_value=mock_response)
        result = client.search_by_serial("987", "TYPE")
        assert result.result_class == CheckResultClass.SUCCESS_WITH_MATCH
        assert len(result.records) == 1
        assert result.records[0]["mi_number"] == "987"

    def test_search_by_serial_eapi_empty_then_type(self, mocker):
        """Тест eapi: пустой ответ, затем доп. запрос с типом."""
        client = ArshinClient()
        client.api_mode = "eapi"
        # Первый запрос — пусто
        mock_empty = {
            "url": "http://test",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {"items": []}
        }
        # Второй запрос — с типом, возвращает результат
        mock_with_type = {
            "url": "http://test?search=TYPE+987",
            "params": {},
            "http_status": 200,
            "response_time_ms": 100,
            "transport_error": None,
            "data": {"items": [{"vri_id": "1", "mi_number": "987"}]}
        }
        mock_make = mocker.patch.object(client, "_make_request", side_effect=[mock_empty, mock_with_type])
        result = client.search_by_serial("987", "TYPE")
        assert len(result.records) == 1
        assert result.records[0]["mi_number"] == "987"
        assert mock_make.call_count == 2

    def test_clear_cache(self):
        client = ArshinClient()
        # Добавляем что-то в кэш
        client._cache["key"] = ArshinSearchResult([])
        assert "key" in client._cache
        client.clear_cache()
        assert client._cache == {}
