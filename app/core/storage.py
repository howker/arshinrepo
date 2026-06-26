from __future__ import annotations

import logging
import os
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class StorageClient:
    """Локальное файловое хранилище (ТЗ §5)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.storage_root = settings.storage_root
        self.uploads_dir = settings.uploads_dir
        self.results_dir = settings.results_dir

        # Создаём директории при инициализации
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self,
        relative_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Сохранить файл в локальное хранилище.
        
        Args:
            relative_path: путь относительно storage_root (напр. "uploads/job_id/file.xlsx")
            data: содержимое файла
            content_type: MIME-тип (игнорируется для локального диска)
        
        Returns:
            Абсолютный путь к сохранённому файлу
        """
        full_path = self.storage_root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(data)
        
        logger.info(f"Saved file to {full_path} ({len(data)} bytes)")
        return str(full_path)

    def download_file(self, relative_path: str) -> bytes:
        """Прочитать файл из локального хранилища.
        
        Args:
            relative_path: путь относительно storage_root
        
        Returns:
            Содержимое файла
        """
        full_path = self.storage_root / relative_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        
        with open(full_path, "rb") as f:
            return f.read()

    def delete_file(self, relative_path: str) -> None:
        """Удалить файл из локального хранилища."""
        full_path = self.storage_root / relative_path
        
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted file {full_path}")


storage = StorageClient()
