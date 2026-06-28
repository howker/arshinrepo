from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import JobStatus


class Job(BaseModel):
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        default=JobStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    result_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    report_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ambiguous_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_uncertain_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    placeholder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Отношения
    items = relationship("JobItem", back_populates="job", cascade="all, delete-orphan")
    issues = relationship("JobIssue", back_populates="job", cascade="all, delete-orphan")
    files = relationship("FileObject", back_populates="job", cascade="all, delete-orphan")
    user = relationship("User", back_populates="jobs")
