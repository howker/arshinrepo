from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import FileObjectType, JobIssueSeverity, JobStatus


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


class JobIssueResponse(BaseModel):
    id: UUID
    job_id: UUID
    job_item_id: UUID | None = None
    code: str
    severity: JobIssueSeverity
    sheet_name: str | None = None
    row_number: int | None = None
    cell_ref: str | None = None
    message: str
    details: dict | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FileObjectResponse(BaseModel):
    id: UUID
    object_type: FileObjectType
    original_filename: str
    storage_bucket: str
    storage_key: str
    content_type: str | None = None
    size_bytes: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RunJobResponse(BaseModel):
    job_id: UUID
    status: JobStatus

    model_config = ConfigDict(from_attributes=True)
