from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task

from app.core.db import SessionLocal
from app.models.job import Job
from app.models.enums import JobStatus

logger = logging.getLogger(__name__)


@shared_task(name="process_excel_job")
def process_excel_job(job_id_str: str) -> str:
    """Заглушка задачи обработки Excel (полная реализация на Э3-Э5).
    
    На Э2 только меняет статус UPLOADED/QUEUED -> COMPLETED.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id_str).first()
        if not job:
            logger.error("Job %s not found", job_id_str)
            return "Job not found"

        logger.info("Processing job %s (stub implementation)", job_id_str)

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        # Здесь будет реальная обработка на Э3-Э5:
        # 1. Парсинг Excel (app/excel/parser.py)
        # 2. Матчинг с Аршином (app/services/matcher.py)
        # 3. Сравнение (app/services/comparator.py)
        # 4. Аннотация результата (app/excel/annotator.py)
        # 5. Генерация отчёта (app/services/report.py)

        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Job %s completed (stub)", job_id_str)
        return "Job completed (stub)"

    except Exception as e:
        logger.exception("Job %s processing failed", job_id_str)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        return f"Job failed: {e}"
    finally:
        db.close()
