from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ExtractedDeviceDTO(BaseModel):
    row_number: int
    group_name: str
    type_val: str | None = None
    serial_number: str
    transformation_ratio: str | None = None
    accuracy_class: str | None = None
    manufacture_year: str | None = None
    verification_date_raw: str | None = None
    next_verification_date_raw: str | None = None
    arshin_link_raw: str | None = None
    
    # Метаданные строки для привязки контекста
    sub_company: str | None = None
    object_name: str | None = None
    connection_point: str | None = None

    model_config = ConfigDict(frozen=True)
