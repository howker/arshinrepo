from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password, get_password_hash
from app.models import User
from app.repositories.users import UserRepository


class AuthenticationError(ValueError):
    pass


class RegistrationError(ValueError):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def authenticate_user(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)

        if user is None:
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        return user

    def register_user(
        self, email: str, password: str, invite_code: str, full_name: str | None = None,
    ) -> User:
        """Саморегистрация метролога по коду приглашения.

        Каждый видит только свои файлы. Код приглашения защищает сервис
        от посторонних аккаунтов, которые без ограничений нагружали бы
        ФГИС «Аршин» — реестр общедоступен, но нагрузку на него мы бережём.
        """
        from app.core.config import get_settings
        from app.models.enums import UserRole

        expected = get_settings().registration_invite_code
        if not expected or invite_code != expected:
            raise RegistrationError("Неверный код приглашения")

        if self.users.get_by_email(email) is not None:
            raise RegistrationError("Пользователь с таким email уже зарегистрирован")

        user = User(
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=UserRole.USER,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_token_for_user(self, user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": str(user.role.value if hasattr(user.role, "value") else user.role),
            },
        )
