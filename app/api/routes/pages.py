from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

from app.api.deps import get_current_user_optional
from app.models.user import User

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/web_templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse(url="/", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request, user: User = Depends(get_current_user_optional)):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: str, user: User = Depends(get_current_user_optional)):
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse("job_detail.html", {"request": request, "user": user})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    response.delete_cookie("token")
    return response
