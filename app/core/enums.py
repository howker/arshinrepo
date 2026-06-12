from enum import StrEnum


class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ISSUES = "completed_with_issues"
    FAILED = "failed"


class FileObjectKind(StrEnum):
    SOURCE = "source"
    RESULT = "result"
    REPORT = "report"


class JobItemStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueCode(StrEnum):
    TYPE_MISMATCH = "TYPE_MISMATCH"
    SERIAL_MISMATCH = "SERIAL_MISMATCH"
    VERIFICATION_DATE_MISMATCH = "VERIFICATION_DATE_MISMATCH"
    NEXT_VERIFICATION_DATE_MISMATCH = "NEXT_VERIFICATION_DATE_MISMATCH"
    ARSHIN_NOT_FOUND = "ARSHIN_NOT_FOUND"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    PLACEHOLDER_VALUE_DETECTED = "PLACEHOLDER_VALUE_DETECTED"
    LINK_MISMATCH = "LINK_MISMATCH"
