import logging
import httpx
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.schemas.arshin import ArshinRecordDTO

logger = logging.getLogger(__name__)

class ArshinClientAdapter:
    def __init__(self, base_url: str = "https://fgis.gost.ru/fundmetrology/e-registry/vri/api/v1"):
        # Если API изменится, достаточно поменять этот URL в конфиге
        self.base_url = base_url
        self.timeout = httpx.Timeout(15.0, connect=5.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    def search_device(self, type_val: str, serial_number: str) -> List[ArshinRecordDTO]:
        """
        Изолированный контракт запроса к Аршину.
        Возвращает список найденных поверок (их может быть несколько для одного прибора).
        """
        if not type_val or not serial_number:
            return []

        # TODO: Заменить на точный эндпоинт, когда контракт Аршина будет финализирован.
        # Пока используем mock-подобную структуру для изоляции бизнес-логики.
        search_url = f"{self.base_url}/records"
        params = {
            "search": f"{type_val} {serial_number}",
            "start": 0,
            "rows": 10
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return self._parse_arshin_response(data)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            logger.error(f"Arshin API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Arshin API request failed: {e}")
            raise

    def _parse_arshin_response(self, raw_data: dict) -> List[ArshinRecordDTO]:
        """
        Нормализует сырой ответ Аршина в нашу внутреннюю модель ArshinRecordDTO.
        """
        results = []
        items = raw_data.get("items", []) # Предполагаемая структура
        
        for item in items:
            try:
                # Маппинг полей (требует адаптации под реальный JSON Аршина)
                record = ArshinRecordDTO(
                    vri_id=str(item.get("vri_id")),
                    mi_mitnumber=item.get("mi.mitnumber"),
                    mi_number=item.get("mi.number"),
                    # is_valid = True если поверка пригодна, и т.д.
                    public_url=f"https://fgis.gost.ru/fundmetrology/cm/results/{item.get('vri_id')}"
                )
                results.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse Arshin item: {item}. Error: {e}")
                
        return results

arshin_client = ArshinClientAdapter()
