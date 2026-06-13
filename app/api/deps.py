from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.user import User

def get_current_user(db: Session = Depends(get_db)) -> User:
    result = db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="admin@arshin.local",
            password_hash="fake_hash",  # Исправлено!
            is_active=True
            # Поле role автоматически получит UserRole.ADMIN
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
