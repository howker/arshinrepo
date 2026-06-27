"""Парсер Excel по JSON-профилю (ТЗ раздел 7)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.excel.normalize import (
    normalize_serial_for_comparison,
    normalize_serial_for_request,
    normalize_string,
    normalize_type,
    to_canonical_date,
    extract_vri_from_link,
)

logger = logging.getLogger(__name__)


class TemplateNotMatchedError(Exception):
    """Лист не соответствует ни одному шаблону."""
    pass


class TemplateDrivenParser:
    """Парсер Excel, управляемый JSON-профилем (ТЗ раздел 7)."""

    def __init__(self, template_code: str, profiles_dir: str = "app/templates_profiles"):
        self.template_code = template_code
        self.profiles_dir = Path(profiles_dir)
        self.config = self._load_profile()

    def _load_profile(self) -> dict:
        profile_path = self.profiles_dir / f"{self.template_code}.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def parse_workspace_file(self, file_path: str) -> list[dict]:
        """Основной метод парсинга."""
        wb = load_workbook(file_path, data_only=True)
        sheet = self._find_sheet(wb)
        if sheet is None:
            raise TemplateNotMatchedError(
                f"Лист не найден по шаблонам: {self.config['sheet_patterns']}"
            )

        rows = list(sheet.iter_rows(values_only=True))
        data_start = self.config['data_start_row'] - 1  # openpyxl 0-index
        skip_markers = self.config.get('skip_row_markers', [])

        context_cols = self.config['context_columns']
        groups = self.config['device_groups']
        link_policy = self.config.get('link_overwrite_policy', 'replace')

        devices = []
        context = {}  # forward-fill контекста

        for row_idx in range(data_start, len(rows)):
            row = rows[row_idx]
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue

            # Пропуск строк с маркерами
            if any(str(cell).strip() in skip_markers for cell in row if cell is not None):
                continue

            # Обновляем контекст (forward-fill)
            for key, col_num in context_cols.items():
                val = row[col_num - 1] if col_num - 1 < len(row) else None
                if val is not None and str(val).strip() not in ('', '-', '—'):
                    context[key] = normalize_string(val)

            # Парсим группы приборов
            for group in groups:
                presence_col = group['presence_column'] - 1
                serial_val = row[presence_col] if presence_col < len(row) else None
                serial_raw = normalize_serial_for_request(serial_val)
                # Если серийник пустой или маркер отсутствия — пропускаем
                if not serial_raw or serial_raw in ('-', '—', 'нет'):
                    continue

                # Извлекаем значения по колонкам
                cols = group['columns']
                device = {
                    'sheet_name': sheet.title,
                    'excel_row': row_idx + 1,
                    'device_kind': group['device_kind'],
                    'block_code': group['block_code'],
                    'type_raw': row[cols['type'] - 1] if cols['type'] - 1 < len(row) else None,
                    'type_norm': normalize_type(row[cols['type'] - 1] if cols['type'] - 1 < len(row) else None),
                    'serial_raw': serial_raw,
                    'serial_norm': normalize_serial_for_comparison(serial_raw),
                    'accuracy_class_raw': row[cols['accuracy_class'] - 1] if cols['accuracy_class'] - 1 < len(row) else None,
                    'verification_date_raw': row[cols['verification_date'] - 1] if cols['verification_date'] - 1 < len(row) else None,
                    'verification_date_norm': to_canonical_date(row[cols['verification_date'] - 1] if cols['verification_date'] - 1 < len(row) else None),
                    'next_date_raw': row[cols['next_verification_date'] - 1] if cols['next_verification_date'] - 1 < len(row) else None,
                    'next_date_norm': to_canonical_date(row[cols['next_verification_date'] - 1] if cols['next_verification_date'] - 1 < len(row) else None),
                    'link_raw': row[cols['arshin_link'] - 1] if cols['arshin_link'] - 1 < len(row) else None,
                    'link_vri': extract_vri_from_link(row[cols['arshin_link'] - 1] if cols['arshin_link'] - 1 < len(row) else None),
                    'context': context.copy(),
                    'cell_refs': {
                        'type': self._cell_ref(row_idx + 1, cols['type']),
                        'serial': self._cell_ref(row_idx + 1, cols['serial']),
                        'verification_date': self._cell_ref(row_idx + 1, cols['verification_date']),
                        'next_date': self._cell_ref(row_idx + 1, cols['next_verification_date']),
                        'link': self._cell_ref(row_idx + 1, cols['arshin_link']),
                    }
                }
                devices.append(device)

        return devices

    def _find_sheet(self, wb):
        patterns = self.config.get('sheet_patterns', [])
        for sheet in wb.worksheets:
            title = sheet.title
            for pattern in patterns:
                if pattern in title:
                    return sheet
        return None

    def _cell_ref(self, row: int, col: int) -> str:
        from openpyxl.utils import get_column_letter
        return f"{get_column_letter(col)}{row}"
