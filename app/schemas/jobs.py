from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import FileObjectType, IssueCode, JobIssueSeverity, JobStatus


class JobResponse(BaseModel):
    """DTO для Job (ТЗ §4.2)."""
    id: UUID
    status: JobStatus
    source_filename: str
    total_items: int
    matched_count: int
    mismatch_count: int
    ambiguous_count: int
    source_uncertain_count: int
    placeholder_count: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    @computed_field
    @property
    def result_available(self) -> bool:
        """Флаг доступности результата для скачивания (ТЗ §13)."""
        return self.status in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ISSUES}

    model_config = ConfigDict(from_attributes=True)


class JobIssueResponse(BaseModel):
    """DTO для JobIssue (ТЗ §4.6)."""
    id: UUID
    job_id: UUID
    job_item_id: UUID | None = None
    sheet_name: str | None = None
    cell: str | None = None
    severity: JobIssueSeverity
    code: IssueCode
    message: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FileObjectResponse(BaseModel):
    """DTO для FileObject (ТЗ §4.3)."""
    id: UUID
    job_id: UUID
    kind: FileObjectType
    path: str
    size_bytes: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RunJobResponse(BaseModel):
    """Ответ на POST /api/jobs/{id}/run."""
    job_id: UUID
    status: JobStatus

    model_config = ConfigDict(from_attributes=True)
