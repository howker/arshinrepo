from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models import User
from app.repositories.users import UserRepository


class AuthenticationError(ValueError):
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

    def create_token_for_user(self, user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra_claims={
                "email": user.email,
                "role": str(user.role.value if hasattr(user.role, "value") else user.role),
            },
        )
