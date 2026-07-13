"""Приоритеты очереди обработки.

Пропускная способность Аршина ограничена (один запрос в ~2 секунды), поэтому
задачи выполняются последовательно. Чтобы короткая проверка не ждала часами
за чужим большим файлом, приоритет назначается по числу приборов.

Celery + Redis: 0 — наивысший приоритет, 9 — наинизший.
"""
from __future__ import annotations

import logging

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


def count_devices_in_file(file_path: str, template_code: str = "auto") -> int:
    """Считает приборы в файле, чтобы назначить приоритет.

    Парсинг локальный, к Аршину не обращается.
    """
    try:
        from app.excel.parser import TemplateDrivenParser
        parser = TemplateDrivenParser()
        return len(parser.parse_workspace_file(file_path))
    except Exception as e:
        logger.warning("Не удалось посчитать приборы для приоритета: %s", e)
        return 0
