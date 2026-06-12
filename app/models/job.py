from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import JobStatus


class Job(BaseModel):
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_objects.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    result_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_objects.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        default=JobStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)

    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mismatched_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_found_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    multiple_match_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="jobs")
    source_file = relationship(
        "FileObject",
        foreign_keys=[source_file_id],
        back_populates="source_job",
    )
    result_file = relationship(
        "FileObject",
        foreign_keys=[result_file_id],
        back_populates="result_job",
    )
    items = relationship("JobItem", back_populates="job", cascade="all, delete-orphan")
    issues = relationship("JobIssue", back_populates="job", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="job")
