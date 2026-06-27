from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import JobItemStatus


class JobItem(BaseModel):
    __tablename__ = "job_items"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    excel_row: Mapped[int] = mapped_column(Integer, nullable=False)

    device_kind: Mapped[str] = mapped_column(String(10), nullable=False)  # si|ct|vt
    block_code: Mapped[str] = mapped_column(String(50), nullable=False)

    type_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_norm: Mapped[str | None] = mapped_column(String(255), nullable=True)

    serial_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_norm: Mapped[str | None] = mapped_column(String(255), nullable=True)

    accuracy_class_raw: Mapped[str | None] = mapped_column(String(50), nullable=True)

    verification_date_file_raw: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verification_date_file_norm: Mapped[date | None] = mapped_column(Date, nullable=True)

    next_date_file_raw: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_date_file_norm: Mapped[date | None] = mapped_column(Date, nullable=True)

    link_file_raw: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    link_file_vri: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cell_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cell_serial: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cell_verification_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cell_next_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cell_link: Mapped[str | None] = mapped_column(String(20), nullable=True)

    context_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[JobItemStatus] = mapped_column(
        Enum(JobItemStatus, name="job_item_status_enum"),
        default=JobItemStatus.PENDING,
        nullable=False,
        index=True,
    )

    job = relationship("Job", back_populates="items")
    checks = relationship("JobItemCheck", back_populates="job_item", cascade="all, delete-orphan")
    issues = relationship("JobIssue", back_populates="job_item", cascade="all, delete-orphan")
