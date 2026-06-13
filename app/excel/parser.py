import json
import os
import logging
from typing import List, Dict, Any
import openpyxl
from app.schemas.devices import ExtractedDeviceDTO

logger = logging.getLogger(__name__)

class TemplateDrivenParser:
    def __init__(self, template_code: str = "pril_1_main"):
        self.template_code = template_code
        self.config = self._load_template_config(template_code)

    def _load_template_config(self, code: str) -> Dict[str, Any]:
        # В MVP ищем файл конфигурации в директории templates
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_path = os.path.join(base_dir, "templates", f"{code}.json")
        if not os.path.exists(config_path):
            raise ValueError(f"Template profile configuration for '{code}' not found.")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_workspace_file(self, file_path: str) -> List[ExtractedDeviceDTO]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet_name = self.config.get("sheet_name")
        
        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.active
            
        extracted_devices: List[ExtractedDeviceDTO] = []
        start_row = self.config.get("data_start_row", 10)
        
        # Переменные для forward-fill (наследования) метаданных строки
        current_meta: Dict[str, Any] = {}
        meta_cfg = self.config.get("meta_columns", {})

        for row_idx in range(start_row, ws.max_row + 1):
            # Проверяем, пустая ли строка вообще
            row_cells = [ws.cell(row=row_idx, column=c).value for c in range(1, 15)]
            if not any(row_cells):
                continue
                
            # Пропускаем строки с ошибками формул типа #NAME?
            if any(str(cell).startswith("#NAME?") for cell in row_cells if cell):
                logger.warning(f"Skipping calculated garbage row {row_idx} due to formula errors.")
                continue

            # Обновляем метаданные, если в текущей строке они заполнены
            meta_updated = False
            for field_name, col_num in meta_cfg.items():
                val = ws.cell(row=row_idx, column=col_num).value
                if val is not None:
                    current_meta[field_name] = str(val).strip()
                    meta_updated = True

            # Парсим группы устройств на этой строке
            for group in self.config.get("device_groups", []):
                group_name = group["group_name"]
                req_col = group["required_column_index"]
                
                # Проверяем наличие ключевого признака устройства (заводской номер)
                serial_val = ws.cell(row=row_idx, column=req_col).value
                if serial_val is None or str(serial_val).strip() == "" or str(serial_val).strip().upper() == "НЕТ":
                    continue
                    
                cols = group["columns"]
                
                def get_val(key: str) -> str | None:
                    c_num = cols.get(key)
                    if not c_num:
                        return None
                    v = ws.cell(row=row_idx, column=c_num).value
                    return str(v).strip() if v is not None else None

                device_dto = ExtractedDeviceDTO(
                    row_number=row_idx,
                    group_name=group_name,
                    type_val=get_val("type"),
                    serial_number=str(serial_val).strip(),
                    transformation_ratio=get_val("transformation_ratio"),
                    accuracy_class=get_val("accuracy_class"),
                    manufacture_year=get_val("manufacture_year"),
                    verification_date_raw=get_val("verification_date"),
                    next_verification_date_raw=get_val("next_verification_date"),
                    arshin_link_raw=get_val("arshin_link"),
                    sub_company=current_meta.get("sub_company"),
                    object_name=current_meta.get("object_name"),
                    connection_point=current_meta.get("connection_point")
                )
                extracted_devices.append(device_dto)

        return extracted_devices
