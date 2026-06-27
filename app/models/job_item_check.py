from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CheckResultClass


class JobItemCheck(BaseModel):
    __tablename__ = "job_item_checks"

    job_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    arshin_found: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    selected_vri_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    arshin_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    arshin_serial: Mapped[str | None] = mapped_column(String(255), nullable=True)

    arshin_verification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    arshin_valid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    arshin_applicability: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    candidates_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_class: Mapped[CheckResultClass] = mapped_column(
        Enum(CheckResultClass, name="check_result_class_enum"),
        nullable=False,
        index=True,
    )

    job_item = relationship("JobItem", back_populates="checks")
