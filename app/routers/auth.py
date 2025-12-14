from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import login_user, logout_user, verify_password
from app.db import get_db
from app.models import Role, User


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    user = db.scalar(select(User).where(User.id == int(user_id)))
    if not user:
        request.session.pop("user_id", None)
        return RedirectResponse("/login", status_code=303)
    if user.role == Role.student:
        return RedirectResponse("/student", status_code=303)
    return RedirectResponse("/teacher", status_code=303)


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    university_id: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.university_id == university_id))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid ID or password."},
            status_code=401,
        )
    login_user(request, user)
    if user.role == Role.student:
        return RedirectResponse("/student", status_code=303)
    return RedirectResponse("/teacher", status_code=303)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/login", status_code=303)

