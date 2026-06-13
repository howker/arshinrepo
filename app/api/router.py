from fastapi import APIRouter
from app.api.routes import jobs

from app.api.routes.auth import router as auth_router

apirouter = APIRouter()
apirouter.include_router(auth_router)

apirouter.include_router(jobs.router)
