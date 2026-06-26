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
    FAILED_SOURCE_UNAVAILABLE = "failed_source_unavailable"


class FileObjectType(StrEnum):
    SOURCE = "source"
    RESULT = "result"
    REPORT = "report"


class JobItemStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    MISMATCH = "mismatch"
    AMBIGUOUS = "ambiguous"
    SOURCE_UNCERTAIN = "source_uncertain"
    PLACEHOLDER = "placeholder"
    MISSING_DATA = "missing_data"
    ERROR = "error"


class JobIssueSeverity(StrEnum):
    """Severity -> цвет заливки в Excel (ТЗ раздел 12)."""
    RED = "red"
    YELLOW = "yellow"
    ORANGE = "orange"
    INFO = "info"


class IssueCode(StrEnum):
    MATCH = "MATCH"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    SERIAL_MISMATCH = "SERIAL_MISMATCH"
    VERIFICATION_DATE_MISMATCH = "VERIFICATION_DATE_MISMATCH"
    NEXT_VERIFICATION_DATE_MISMATCH = "NEXT_VERIFICATION_DATE_MISMATCH"
    LINK_MISMATCH = "LINK_MISMATCH"
    LINK_FILLED = "LINK_FILLED"
    PLACEHOLDER_VALUE_DETECTED = "PLACEHOLDER_VALUE_DETECTED"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    ARSHIN_NOT_FOUND = "ARSHIN_NOT_FOUND"
    SOURCE_UNCERTAIN = "SOURCE_UNCERTAIN"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"


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


class CheckResultClass(StrEnum):
    """Классификация результата попытки запроса к Аршину (ТЗ раздел 9.3)."""
    SUCCESS_WITH_MATCH = "success_with_match"
    SUCCESS_EMPTY = "success_empty"
    TEMPORARY_SOURCE_FAILURE = "temporary_source_failure"
    AMBIGUOUS_MULTIPLE_MATCHES = "ambiguous_multiple_matches"


class AuditAction(StrEnum):
    LOGIN = "login"
    UPLOAD_CREATED = "upload_created"
    JOB_RUN_REQUESTED = "job_run_requested"
    JOB_PROCESSING_STARTED = "job_processing_started"
    JOB_PROCESSING_COMPLETED = "job_processing_completed"
    JOB_PROCESSING_FAILED = "job_processing_failed"
    FILE_DOWNLOADED = "file_downloaded"
