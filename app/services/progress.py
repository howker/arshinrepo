"""Расчёт прогресса обработки и позиции в очереди.

Ничего не запрашивает у Аршина — работает только с нашей БД.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_event import JobEvent
from app.models.enums import JobStatus

# Средняя скорость обработки прибора, если статистики ещё нет.
# Соответствует паузе между запросами к Аршину.
DEFAULT_SECONDS_PER_ITEM = 2.5

MAX_EVENTS = 500


def _queue_position(db: Session, job: Job) -> int | None:
    """Сколько задач стоит перед этой.

    Порядок соответствует приоритетной очереди: сначала более приоритетные
    (короткие файлы), при равном приоритете — кто раньше встал.
    """
    if job.status != JobStatus.QUEUED:
        return None

    stmt = select(Job).where(Job.status == JobStatus.QUEUED)
    queued = db.execute(stmt).scalars().all()

    ahead = 0
    for other in queued:
        if other.id == job.id:
            continue
        # Более высокий приоритет = меньше число
        if other.priority < job.priority:
            ahead += 1
        elif other.priority == job.priority:
            a = other.queued_at or other.created_at
            b = job.queued_at or job.created_at
            if a and b and a < b:
                ahead += 1
    return ahead + 1


def _timing(job: Job) -> tuple[int | None, int | None]:
    """Сколько прошло и сколько примерно осталось (в секундах)."""
    if not job.started_at:
        return None, None

    now = datetime.now(timezone.utc)
    started = job.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)

    finished = job.finished_at
    if finished:
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        return int((finished - started).total_seconds()), 0

    elapsed = int((now - started).total_seconds())

    remaining = max(0, (job.total_items or 0) - (job.processed_items or 0))
    if not remaining:
        return elapsed, 0

    # Скорость по факту, если уже что-то обработано
    if job.processed_items and job.processed_items > 0:
        per_item = elapsed / job.processed_items
    else:
        per_item = DEFAULT_SECONDS_PER_ITEM

    return elapsed, int(remaining * per_item)


def build_progress(db: Session, job: Job, after_id: uuid.UUID | None = None) -> dict:
    """Собирает состояние прогресса для интерфейса."""
    elapsed, eta = _timing(job)

    stmt = (
        select(JobEvent)
        .where(JobEvent.job_id == job.id)
        .order_by(JobEvent.created_at.asc(), JobEvent.id.asc())
        .limit(MAX_EVENTS)
    )
    events = db.execute(stmt).scalars().all()

    return {
        "job_id": job.id,
        "status": job.status,
        "total_items": job.total_items or 0,
        "processed_items": job.processed_items or 0,
        "current_item_label": job.current_item_label,
        "queue_position": _queue_position(db, job),
        "elapsed_seconds": elapsed,
        "eta_seconds": eta,
        "matched_count": job.matched_count or 0,
        "mismatch_count": job.mismatch_count or 0,
        "ambiguous_count": job.ambiguous_count or 0,
        "source_uncertain_count": job.source_uncertain_count or 0,
        "events": events,
    }
