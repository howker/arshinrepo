from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import FileObjectType


class FileObject(BaseModel):
    __tablename__ = "file_objects"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    object_type: Mapped[FileObjectType] = mapped_column(
        Enum(FileObjectType, name="file_object_type_enum"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    source_job = relationship(
        "Job",
        foreign_keys="Job.source_file_id",
        back_populates="source_file",
        uselist=False,
    )
    result_job = relationship(
        "Job",
        foreign_keys="Job.result_file_id",
        back_populates="result_file",
        uselist=False,
    )
