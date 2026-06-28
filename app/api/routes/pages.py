from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.status import HTTP_302_FOUND
import jinja2

from app.api.deps import get_current_user_optional
from app.models.user import User

router = APIRouter(tags=["Pages"])

template_loader = jinja2.FileSystemLoader(searchpath="app/web_templates")
template_env = jinja2.Environment(loader=template_loader, autoescape=True)

def render_template(template_name: str, request: Request, context: dict):
    template = template_env.get_template(template_name)
    context["request"] = request
    return HTMLResponse(content=template.render(context))

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    # НЕ редиректим на / по cookie: авторизация живёт в localStorage, гейт делает JS
    return render_template("login.html", request, {})

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    # Всегда отдаём страницу. Гейт — в index.html (if !token -> /login). Данные защищены на /api/*
    return render_template("index.html", request, {"user": user})

@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: str, user: User | None = Depends(get_current_user_optional)):
    return render_template("job_detail.html", request, {"user": user})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    response.delete_cookie("token")
    return response
