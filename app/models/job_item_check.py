from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CheckStatus


class JobItemCheck(BaseModel):
    __tablename__ = "job_item_checks"

    job_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[CheckStatus] = mapped_column(
        Enum(CheckStatus, name="check_status_enum"),
        default=CheckStatus.PENDING,
        nullable=False,
        index=True,
    )

    request_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    transport_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    selected_vri_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_mi_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_verification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    selected_next_verification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    selected_arshin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    comparison_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job_item = relationship("JobItem", back_populates="checks")
