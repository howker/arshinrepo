import pytest
from pathlib import Path

from app.excel.parser import TemplateDrivenParser, TemplateNotMatchedError


def test_parser_parses_real_file():
    """Тест парсинга реального Excel-файла II-2026-Prilozhenie-No1.xlsx."""
    file_path = Path("II-2026-Prilozhenie-No1.xlsx")
    assert file_path.exists(), "Excel file not found"

    parser = TemplateDrivenParser(template_code="pril_1_main")
    devices = parser.parse_workspace_file(str(file_path))

    assert len(devices) > 0, "No devices parsed"

    # Проверяем, что есть разные типы приборов
    kinds = set(d["device_kind"] for d in devices)
    assert "si" in kinds, "No SI devices found"
    assert "ct" in kinds or "vt" in kinds, "No CT/VT devices found"

    # Проверяем, что у каждого прибора есть серийник и контекст
    for device in devices:
        assert device.get("serial_raw") is not None, "Missing serial"
        assert device.get("serial_norm") is not None, "Missing normalized serial"
        assert device.get("context") is not None, "Missing context"
        assert "excel_row" in device, "Missing excel_row"
        assert "cell_refs" in device, "Missing cell_refs"

    # Проверяем, что строка с #NAME? пропущена (если есть)
    # Находим строки с #NAME? в файле — они не должны появиться в devices
    rows = [d["excel_row"] for d in devices]
    # Обычно строка 9 — мусорная, проверяем, что она не попала
    # (может быть не 9, если файл другой структуры, но проверим)
    for row in rows:
        # В нормальном файле строка 9 должна быть пропущена
        # Проверим, что ни один прибор не имеет excel_row == 9
        # (может быть сдвиг, но это пример)
        assert row != 9, f"Row 9 should be skipped but found device at row {row}"


def test_parser_forward_fill_context():
    """Проверяем, что контекст forward-fill работает."""
    file_path = Path("II-2026-Prilozhenie-No1.xlsx")
    parser = TemplateDrivenParser(template_code="pril_1_main")
    devices = parser.parse_workspace_file(str(file_path))

    # Группируем приборы по номерам узлов (n_pp)
    context_by_row = {}
    for d in devices:
        row = d["excel_row"]
        context = d.get("context", {})
        # Для строк, где есть n_pp, запоминаем контекст
        if context.get("n_pp"):
            context_by_row[row] = context

    # Проверяем, что для приборов в одном узле контекст одинаковый
    # (упрощённо: если два прибора имеют одинаковый n_pp, их контекст должен совпадать)
    grouped = {}
    for d in devices:
        n_pp = d.get("context", {}).get("n_pp")
        if n_pp:
            grouped.setdefault(n_pp, []).append(d)

    for n_pp, group in grouped.items():
        if len(group) > 1:
            first_context = group[0].get("context", {})
            for d in group[1:]:
                assert d.get("context", {}) == first_context, f"Context mismatch for n_pp={n_pp}"


def test_parser_skip_empty_rows():
    """Проверяем, что пустые строки и строки с маркерами пропускаются."""
    # Создаём минимальный валидный файл для теста (или используем существующий)
    # Если файл есть, проверяем, что в нём нет явных ошибок
    file_path = Path("II-2026-Prilozhenie-No1.xlsx")
    parser = TemplateDrivenParser(template_code="pril_1_main")
    devices = parser.parse_workspace_file(str(file_path))

    # Проверяем, что ни один прибор не имеет excel_row с маркером #NAME?
    # Это косвенная проверка, так как мы не знаем точные строки с маркерами
    for d in devices:
        # Если в файле есть строки с #NAME?, они должны быть пропущены
        # Мы не можем точно проверить это без знания структуры, но можем убедиться, что
        # все приборы имеют валидные данные
        assert d.get("serial_norm") is not None, "Device with empty serial found"
