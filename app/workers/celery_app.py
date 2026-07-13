from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "arshin_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Приоритетная очередь: короткие файлы обрабатываются раньше длинных,
    # чтобы проверка на 20 приборов не ждала три часа за файлом на 2000.
    # Без этих опций Redis молча игнорирует приоритеты и работает как FIFO.
    task_queue_max_priority=9,
    task_default_priority=5,
    broker_transport_options={
        # Разделитель по умолчанию Kombu для Redis — \x06\x16.
        # Задавать свой (например ":") нельзя: воркер слушает подочереди,
        # сформированные штатным разделителем, и задачи с другим ключом
        # (celery3, celery5, …) просто повисают непрочитанными.
        "queue_order_strategy": "priority",
        "priority_steps": [0, 3, 6, 9],
        "sep": "\x06\x16",
    },
    # Воркер берёт по одной задаче — иначе он заранее заберёт себе несколько
    # и приоритет вновь поступивших коротких файлов не сработает.
    worker_prefetch_multiplier=1,
    # acks_late=False принципиально: проверка на 2000 приборов идёт больше часа,
    # и при late-ack любой перезапуск воркера возвращал бы задачу в очередь —
    # она стартовала бы заново с нуля, заново нагружая Аршин. Прогресс мы и так
    # храним в БД, поэтому потеря задачи при падении воркера не страшна:
    # метролог просто нажмёт «Запустить проверку» ещё раз.
    task_acks_late=False,
    task_reject_on_worker_lost=False,
)
import app.workers.tasks
