from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import JobIssueSeverity


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

    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[JobIssueSeverity] = mapped_column(
        Enum(JobIssueSeverity, name="job_issue_severity_enum"),
        nullable=False,
        index=True,
    )
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_number: Mapped[int | None] = mapped_column(nullable=True)
    cell_ref: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job = relationship("Job", back_populates="issues")
    job_item = relationship("JobItem", back_populates="issues")
