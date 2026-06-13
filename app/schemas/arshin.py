from pydantic import BaseModel, ConfigDict
from datetime import date

class ArshinRecordDTO(BaseModel):
    vri_id: str
    mi_mitnumber: str | None = None  # Тип СИ
    mi_mititle: str | None = None    # Наименование СИ
    mi_number: str | None = None     # Заводской номер
    verification_date: date | None = None
    valid_date: date | None = None
    is_valid: bool = True
    public_url: str | None = None

    model_config = ConfigDict(frozen=True)
