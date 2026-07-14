"""Простые лимиты через Redis — без сторонних библиотек.

Защищают не пользователя, а сам сервис и Аршин: без ограничений один
скомпрометированный или неаккуратный аккаунт мог бы поставить в очередь
десятки задач по тысячам приборов и застопорить обработку для всех.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.core.redis_client import get_redis_client

# Сколько задач одного пользователя может одновременно быть в очереди/работе.
# Пропускная способность Аршина общая на всех — больше пары параллельных
# больших проверок от одного человека не имеет смысла.
MAX_ACTIVE_JOBS_PER_USER = 3

# Попыток регистрации с одного IP за окно — защита от перебора кода
# приглашения и от массового создания аккаунтов при его утечке.
REGISTER_ATTEMPTS_PER_WINDOW = 5
REGISTER_WINDOW_SECONDS = 3600


def check_active_jobs_limit(db, user_id) -> None:
    """Не даёт поставить в очередь больше MAX_ACTIVE_JOBS_PER_USER задач."""
    from app.models.job import Job
    from app.models.enums import JobStatus

    active = (
        db.query(Job)
        .filter(
            Job.user_id == user_id,
            Job.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING]),
        )
        .count()
    )
    if active >= MAX_ACTIVE_JOBS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=(
                f"У вас уже {active} проверок в очереди или в работе "
                f"(максимум {MAX_ACTIVE_JOBS_PER_USER} одновременно). "
                f"Дождитесь завершения или прервите одну из них."
            ),
        )


def check_register_rate_limit(client_ip: str) -> None:
    """Не больше REGISTER_ATTEMPTS_PER_WINDOW регистраций с одного IP в час."""
    try:
        r = get_redis_client()
        key = f"register_attempts:{client_ip}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, REGISTER_WINDOW_SECONDS)
        if count > REGISTER_ATTEMPTS_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail="Слишком много попыток регистрации. Попробуйте позже.",
            )
    except HTTPException:
        raise
    except Exception:
        # Redis недоступен — не блокируем регистрацию из-за инфраструктурной ошибки
        pass
