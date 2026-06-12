from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ISSUES = "completed_with_issues"
    FAILED = "failed"


class FileObjectType(StrEnum):
    SOURCE = "source"
    RESULT = "result"


class JobItemStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    MULTIPLE_MATCHES = "multiple_matches"
    ERROR = "error"


class JobIssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DeviceType(StrEnum):
    SI = "si"
    CT = "ct"
    VT = "vt"
    OTHER = "other"


class CheckStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    MULTIPLE_MATCHES = "multiple_matches"
    FAILED = "failed"


class AuditAction(StrEnum):
    LOGIN = "login"
    UPLOAD_CREATED = "upload_created"
    JOB_RUN_REQUESTED = "job_run_requested"
    JOB_PROCESSING_STARTED = "job_processing_started"
    JOB_PROCESSING_COMPLETED = "job_processing_completed"
    JOB_PROCESSING_FAILED = "job_processing_failed"
    FILE_DOWNLOADED = "file_downloaded"
