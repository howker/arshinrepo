from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.enums import JobStatus

class JobResponse(BaseModel):
    id: UUID
    status: JobStatus
    original_filename: str
    template_code: str
    total_rows: int
    total_items: int
    processed_items: int
    issue_count: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
