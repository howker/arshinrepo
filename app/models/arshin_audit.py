from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CheckResultClass


class ArshinAudit(BaseModel):
    __tablename__ = "arshin_audit"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)

    endpoint_mode: Mapped[str] = mapped_column(String(10), nullable=False)  # eapi|xcdb
    request_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    request_params_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    transport_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_class: Mapped[CheckResultClass] = mapped_column(
        Enum(CheckResultClass, name="check_result_class_enum"),
        nullable=False,
        index=True,
    )

    job = relationship("Job")
