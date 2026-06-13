from typing import List
from pydantic import BaseModel
from app.models.enums import JobItemStatus
from app.schemas.devices import ExtractedDeviceDTO
from app.schemas.arshin import ArshinRecordDTO

class ComparisonIssue(BaseModel):
    code: str
    message: str
    severity: str = "error"  # error, warning, info

class ComparisonResult(BaseModel):
    device: ExtractedDeviceDTO
    status: JobItemStatus
    matched_record: ArshinRecordDTO | None = None
    issues: List[ComparisonIssue] = []
