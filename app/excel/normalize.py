"""Нормализация данных из Excel по ТЗ раздел 8."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, time
from typing import Any


def normalize_string(value: Any) -> str | None:
    """Очистка строки: удаление пробелов, \n, \r, \t, невидимых символов."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    # Удаляем управляющие символы
    value = re.sub(r'[\r\n\t\x00-\x1f\x7f]', '', value)
    # Схлопываем пробелы
    value = ' '.join(value.split())
    value = value.strip()
    return value if value else None


def normalize_serial_for_comparison(value: Any) -> str | None:
    """Нормализация серийного номера для сравнения (ТЗ 8.1)."""
    if value is None:
        return None
    # Приводим к строке
    if not isinstance(value, str):
        value = str(value)
    # Берём часть до '/' (заводской номер)
    if '/' in value:
        value = value.split('/')[0]
    # Очищаем от пробелов и спецсимволов
    cleaned = re.sub(r'[\s\-_\.]', '', value)
    return cleaned.upper() if cleaned else None


def normalize_serial_for_request(value: Any) -> str | None:
    """Очистка серийника для запроса в Аршин (ТЗ 8.1)."""
    if value is None:
        return None
    # Приводим к строке
    if not isinstance(value, str):
        value = str(value)
    # Удаляем только пробелы и переносы, но оставляем спецсимволы
    cleaned = re.sub(r'[\r\n\t\x00-\x1f\x7f]', '', value)
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip() or None


def normalize_type(value: Any) -> str | None:
    """Нормализация типа СИ для сравнения (ТЗ 8.1)."""
    s = normalize_string(value)
    if s is None:
        return None
    # Удаляем пробелы и дефисы, приводим к верхнему регистру
    cleaned = re.sub(r'[\s\-]', '', s)
    return cleaned.upper() if cleaned else None


def to_canonical_date(value: Any) -> date | None | str:
    """Преобразование в canonical date (ТЗ 8.2).
    Возвращает date, None (нет значения) или "INVALID" (заглушка/мусор).
    """
    # None / пусто / явные маркеры отсутствия
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if s == '' or s in ('-', '—', 'нет', 'н/д', 'Н/Д', 'Нет', 'Не указано'):
            return None

    # Число 0 или 0.0 — заглушка
    if isinstance(value, (int, float)):
        if value == 0 or value == 0.0:
            return "INVALID"
        # Excel serial number
        if isinstance(value, (int, float)) and value > 1:
            try:
                base = datetime(1899, 12, 30)
                dt = base + timedelta(days=float(value))
                return dt.date()
            except Exception:
                pass

    # datetime / date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    # time(0,0) — заглушка
    if isinstance(value, time):
        if value.hour == 0 and value.minute == 0 and value.second == 0:
            return "INVALID"

    # Строковые форматы
    if isinstance(value, str):
        s = value.strip()

        # ISO 8601 из Аршина: "2023-06-12T00:00:00Z", "2017-03-31T03:00:00Z".
        # Берём только дату; время/таймзону игнорируем (Аршин отдаёт местное
        # время поверки, смещение не несёт смысла для сравнения по дате).
        m_iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})T', s)
        if m_iso:
            y, mo, d = map(int, m_iso.groups())
            try:
                return date(y, mo, d)
            except ValueError:
                return "INVALID"

        # Заглушка 31.12.1899
        if re.match(r'^31\.?12\.?1899$|^31121899$', s):
            return "INVALID"
        # DD.MM.YYYY
        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', s)
        if m:
            d, m, y = map(int, m.groups())
            if 1990 <= y <= 2100:
                try:
                    return date(y, m, d)
                except ValueError:
                    pass
        # DD.MM.YY
        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{2})$', s)
        if m:
            d, m, y = map(int, m.groups())
            y += 2000 if y < 30 else 1900
            if 1990 <= y <= 2100:
                try:
                    return date(y, m, d)
                except ValueError:
                    pass
        # DDMMYYYY
        m = re.match(r'^(\d{2})(\d{2})(\d{4})$', s)
        if m:
            d, m, y = map(int, m.groups())
            if 1990 <= y <= 2100:
                try:
                    return date(y, m, d)
                except ValueError:
                    pass
        # YYYY-MM-DD
        try:
            dt = datetime.strptime(s, '%Y-%m-%d')
            if 1990 <= dt.year <= 2100:
                return dt.date()
        except ValueError:
            pass
        # Если ничего не подошло
        return "INVALID"

    return "INVALID"


def extract_vri_from_link(value: Any) -> str | None:
    """Извлечение VRI из ссылки (ТЗ 8.3)."""
    if value is None:
        return None
    s = str(value).strip()
    # Пустые или маркеры отсутствия
    if s in ('', '-', '—', '+', 'Паспорт', 'паспорт'):
        return None
    # Ищем ссылку вида .../cm/results/<vri>
    match = re.search(r'/cm/results/([^/?]+)', s)
    if match:
        return match.group(1)
    # Если это просто vri (начинается с 1- или 2-)
    if re.match(r'^[12]-\d+$', s):
        return s
    return None
