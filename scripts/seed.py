"""Seed script: создаёт admin user и template profile pril_1_main."""
import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.template_profile import TemplateProfile
from app.models.enums import UserRole


def seed_admin_user():
    """Создаёт admin user из переменных окружения."""
    db = SessionLocal()
    try:
        email = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("SEED_ADMIN_PASSWORD", "admin123")
        
        # Проверяем, существует ли пользователь
        stmt = select(User).where(User.email == email)
        existing_user = db.execute(stmt).scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Admin user уже существует: {email}")
            return
        
        # Создаём нового пользователя
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True,
            full_name="Admin User",
        )
        db.add(user)
        db.commit()
        print(f"✅ Создан admin user: {email}")
    finally:
        db.close()


def seed_template_profile():
    """Создаёт template profile pril_1_main."""
    db = SessionLocal()
    try:
        code = "pril_1_main"
        
        # Проверяем, существует ли профиль
        stmt = select(TemplateProfile).where(TemplateProfile.code == code)
        existing_profile = db.execute(stmt).scalar_one_or_none()
        
        if existing_profile:
            print(f"✅ Template profile уже существует: {code}")
            return
        
        # JSON-конфиг из ТЗ раздел 6.1
        profile_config = {
            "code": code,
            "title": "Приложение 1.1 (Счётчики, ТТ, ТН)",
            "sheet_patterns": ["Прил.1.1", "Сч,ТТ,ТН", "1.1"],
            "data_start_row": 10,
            "skip_row_markers": ["#NAME?", "#ИМЯ?", "#REF!"],
            "context_columns": {
                "n_pp": 1,
                "sub_company": 2,
                "object_name": 3,
                "inventory_no": 4,
                "connection_point": 5,
                "voltage_level": 6,
                "metering_type": 7,
            },
            "device_groups": [
                {
                    "device_kind": "si",
                    "block_code": "si",
                    "presence_column": 9,
                    "columns": {
                        "type": 8,
                        "serial": 9,
                        "accuracy_class": 10,
                        "manufacture_year": 11,
                        "verification_date": 12,
                        "next_verification_date": 13,
                        "arshin_link": 14,
                    },
                },
                {
                    "device_kind": "ct",
                    "block_code": "ct",
                    "presence_column": 17,
                    "columns": {
                        "type": 15,
                        "transformation_ratio": 16,
                        "serial": 17,
                        "accuracy_class": 18,
                        "manufacture_year": 19,
                        "verification_date": 20,
                        "next_verification_date": 21,
                        "arshin_link": 22,
                    },
                },
                {
                    "device_kind": "vt",
                    "block_code": "vt",
                    "presence_column": 25,
                    "columns": {
                        "type": 23,
                        "transformation_ratio": 24,
                        "serial": 25,
                        "accuracy_class": 26,
                        "manufacture_year": 27,
                        "verification_date": 28,
                        "next_verification_date": 29,
                        "arshin_link": 30,
                    },
                },
            ],
            "link_overwrite_policy": "replace",
        }
        
        # Создаём новый профиль
        profile = TemplateProfile(
            code=code,
            name="Приложение 1.1 (Счётчики, ТТ, ТН)",
            description="Шаблон для парсинга Приложения 1.1 с счётчиками, ТТ и ТН",
            version="1.0.0",
            is_active=True,
            profile_config=profile_config,
        )
        db.add(profile)
        db.commit()
        print(f"✅ Создан template profile: {code}")
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Запуск seed-скрипта...")
    seed_admin_user()
    seed_template_profile()
    print("✅ Seed завершён успешно!")
