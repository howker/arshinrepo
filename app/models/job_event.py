"""Лента событий обработки job — для живого лога в интерфейсе.

Воркер пишет сюда по событию на каждый обработанный прибор, а страница
подтягивает их поллингом. Это внутренняя механика: никакой нагрузки
на ФГИС «Аршин» лог не создаёт.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class JobEvent(BaseModel):
    __tablename__ = "job_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Порядковый номер прибора (1..N); None — служебное событие (старт, финиш)
    item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Уровень: info | success | warning | error
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="info")

    # Текст для метролога, на русском:
    # «Прибор 5 из 20: ЗНОЛ-0.6-10 УЗ № 6590 — расхождение даты поверки»
    message: Mapped[str] = mapped_column(Text, nullable=False)

    job = relationship("Job", back_populates="events")
