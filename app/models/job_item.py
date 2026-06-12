from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DeviceType, JobItemStatus


class JobItem(BaseModel):
    __tablename__ = "job_items"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    device_group: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, name="device_type_enum"),
        nullable=False,
    )

    type_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)

    verification_date_file: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_verification_date_file: Mapped[date | None] = mapped_column(Date, nullable=True)
    arshin_url_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    excel_cell_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    excel_cell_serial: Mapped[str | None] = mapped_column(String(20), nullable=True)
    excel_cell_verification_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    excel_cell_next_verification_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    excel_cell_link: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[JobItemStatus] = mapped_column(
        Enum(JobItemStatus, name="job_item_status_enum"),
        default=JobItemStatus.PENDING,
        nullable=False,
        index=True,
    )
    comment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    job = relationship("Job", back_populates="items")
    checks = relationship("JobItemCheck", back_populates="job_item", cascade="all, delete-orphan")
    issues = relationship("JobIssue", back_populates="job_item", cascade="all, delete-orphan")
