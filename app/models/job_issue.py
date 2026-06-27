from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import IssueCode, JobIssueSeverity


class JobIssue(BaseModel):
    __tablename__ = "job_issues"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cell: Mapped[str | None] = mapped_column(String(20), nullable=True)

    severity: Mapped[JobIssueSeverity] = mapped_column(
        Enum(JobIssueSeverity, name="job_issue_severity_enum"),
        nullable=False,
        index=True,
    )
    code: Mapped[IssueCode] = mapped_column(
        Enum(IssueCode, name="issue_code_enum"),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(Text, nullable=False)

    job = relationship("Job", back_populates="issues")
    job_item = relationship("JobItem", back_populates="issues")
