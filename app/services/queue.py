"""Приоритеты очереди обработки.

Пропускная способность Аршина ограничена (один запрос в ~2 секунды), поэтому
задачи выполняются последовательно. Чтобы короткая проверка не ждала часами
за чужим большим файлом, приоритет назначается по числу приборов.

Celery + Redis: 0 — наивысший приоритет, 9 — наинизший.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Порог по числу приборов -> приоритет
# Значения приоритета должны совпадать с priority_steps в celery_app,
# иначе Kombu округлит их к ближайшей ступени, а задача может уйти
# в подочередь, которую воркер не слушает.
PRIORITY_TIERS = [
    (50, 0),      # до 50 приборов — быстрые проверки идут первыми
    (200, 3),
    (1000, 6),
]
LOWEST_PRIORITY = 9


def priority_for_items(total_items: int) -> int:
    """Приоритет по размеру файла: чем меньше приборов, тем выше."""
    if not total_items or total_items <= 0:
        return 6  # размер неизвестен — средний приоритет
    for threshold, prio in PRIORITY_TIERS:
        if total_items <= threshold:
            return prio
    return LOWEST_PRIORITY


def priority_for_file(file_path: str) -> int:
    """Приоритет по размеру файла в байтах.

    Полный парсинг ради приоритета делать нельзя: на файле в 2000+ приборов
    он занимает ~40 секунд прямо внутри HTTP-запроса — метролог ждёт, а задача
    тем временем уже стартует в воркере, и статусы начинают конфликтовать.
    Размер файла — достаточно хорошая оценка числа приборов.
    """
    try:
        size_kb = os.path.getsize(file_path) / 1024
    except OSError as e:
        logger.warning("Не удалось оценить размер файла: %s", e)
        return 6

    # Эмпирика: ~20 приборов ≈ 30 КБ, ~2260 приборов ≈ 700 КБ
    if size_kb <= 60:
        return 0
    if size_kb <= 200:
        return 3
    if size_kb <= 600:
        return 6
    return LOWEST_PRIORITY
