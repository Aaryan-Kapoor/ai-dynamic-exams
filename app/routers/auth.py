from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import login_user, logout_user, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me", response_model=UserRead)
def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.scalar(select(User).where(User.id == int(user_id)))
    if not user:
        request.session.pop("user_id", None)
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/login", response_model=UserRead)
def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.university_id == payload.university_id))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid ID or password.")
    login_user(request, user)
    return user

@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return {"detail": "Logged out"}

