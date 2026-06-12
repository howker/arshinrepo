from __future__ import annotations

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TemplateProfile(BaseModel):
    __tablename__ = "template_profiles"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_config: Mapped[dict] = mapped_column(JSON, nullable=False)
