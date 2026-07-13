from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import getdb
from app.core.security import TokenPayloadError, decode_access_token
from app.models import User
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services.auth import AuthService, AuthenticationError, RegistrationError

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(getdb),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (TokenPayloadError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or not found",
        )

    return user


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(getdb)) -> TokenResponse:
    """Саморегистрация. После регистрации пользователь сразу авторизован."""
    service = AuthService(db)

    try:
        user = service.register_user(payload.email, payload.password, payload.full_name)
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    token = service.create_token_for_user(user)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(getdb)) -> TokenResponse:
    service = AuthService(db)

    try:
        user = service.authenticate_user(payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    token = service.create_token_for_user(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        fullname=current_user.full_name,
        role=str(current_user.role.value if hasattr(current_user.role, "value") else current_user.role),
        isactive=current_user.is_active,
    )
