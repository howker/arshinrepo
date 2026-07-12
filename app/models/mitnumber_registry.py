"""Кэш соответствий «корень модели СИ → номера госреестра (mitnumber)».

Это НЕ кэш данных о поверках (те всегда берутся живым запросом в Аршин),
а справочник навигации по реестру ТИПОВ СИ. Он позволяет сузить поиск
с тысяч нерелевантных записей (один серийник = 1600+ чужих приборов)
до единиц реально релевантных.
"""
from __future__ import annotations

from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MitnumberRegistry(BaseModel):
    __tablename__ = "mitnumber_registry"

    model_root: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    matched_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    mitnumbers: Mapped[list] = mapped_column(JSONB, nullable=False)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
