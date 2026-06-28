from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.router import apirouter
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Монтируем статику раньше всех роутеров
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(health_router, tags=["health"])
app.include_router(apirouter, prefix=settings.api_prefix)

# Добавляем роутер для страниц
from app.api.routes import pages
app.include_router(pages.router)
