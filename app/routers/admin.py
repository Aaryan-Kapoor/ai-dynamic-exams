from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db import get_db
from app.models import (
    College,
    Department,
    Role,
    User,
)
from app.rbac import require_roles
from app.schemas import (
    CollegeCreate,
    CollegeRead,
    DepartmentCreate,
    DepartmentRead,
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/users", response_model=List[UserRead])
def list_users(
    role: Optional[Role] = None,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    return db.scalars(query).all()


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    target_user = db.scalar(select(User).where(User.id == user_id))
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    return target_user


@router.post("/users", response_model=UserRead)
def create_user(
    payload: UserCreate,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(User).where(User.university_id == payload.university_id))
    if existing:
        raise HTTPException(status_code=400, detail="University ID already exists")

    hashed_pw = pwd_context.hash(payload.password)
    new_user = User(
        university_id=payload.university_id,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hashed_pw,
        college_id=payload.college_id,
        grade_level=payload.grade_level,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(User).where(User.id == user_id))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.role is not None:
        target.role = payload.role
    if payload.college_id is not None:
        target.college_id = payload.college_id
    if payload.grade_level is not None:
        target.grade_level = payload.grade_level
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.password:
        target.password_hash = pwd_context.hash(payload.password)
    
    if payload.department_ids is not None:
        # Update department memberships
        departments = db.scalars(
            select(Department).where(Department.id.in_(payload.department_ids))
        ).all()
        target.departments = list(departments)

    db.commit()
    db.refresh(target)
    return target


@router.get("/colleges", response_model=List[CollegeRead])
def list_colleges(
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    return db.scalars(select(College).order_by(College.name)).all()


@router.post("/colleges", response_model=CollegeRead)
def create_college(
    payload: CollegeCreate,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(College).where(College.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail="College name already exists")
    
    college = College(name=payload.name)
    db.add(college)
    db.commit()
    db.refresh(college)
    return college


@router.post("/departments", response_model=DepartmentRead)
def create_department(
    payload: DepartmentCreate,
    user: User = Depends(require_roles(Role.system_admin)),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(Department)
        .where(Department.college_id == payload.college_id)
        .where(Department.name == payload.name)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists in this college")

    dept = Department(name=payload.name, college_id=payload.college_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept
