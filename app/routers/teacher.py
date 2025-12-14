from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import (
    Department,
    ExamAttempt,
    ExamConfig,
    LectureChunk,
    LectureMaterial,
    Role,
    User,
)
from app.rbac import require_roles
from app.services.lecture_processing import chunk_text, extract_text_from_upload
from app.services.vector_index import ensure_chunk_embeddings


router = APIRouter(prefix="/teacher", tags=["teacher"])
templates = Jinja2Templates(directory="app/templates")


def _accessible_departments(db: Session, user: User) -> list[Department]:
    if user.role in {Role.system_admin}:
        return db.scalars(select(Department).order_by(Department.id)).all()
    if user.role in {Role.college_admin, Role.head} and user.college_id:
        return db.scalars(
            select(Department)
            .where(Department.college_id == user.college_id)
            .order_by(Department.id)
        ).all()
    return list(user.departments)


def _ensure_department_access(db: Session, *, user: User, department_id: int) -> None:
    allowed_ids = {d.id for d in _accessible_departments(db, user)}
    if department_id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Not allowed for this department.")


@router.get("")
def dashboard(
    request: Request,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    departments = _accessible_departments(db, user)
    if not departments:
        raise HTTPException(status_code=403, detail="No departments assigned to this teacher.")

    allowed_ids = {d.id for d in departments}
    department_id = int(request.query_params.get("department_id", departments[0].id))
    if department_id not in allowed_ids:
        department_id = departments[0].id
    grade_level = int(request.query_params.get("grade_level", 1))
    if grade_level not in {1, 2, 3, 4}:
        grade_level = 1

    config = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == department_id)
        .where(ExamConfig.grade_level == grade_level)
    )
    lectures = db.scalars(
        select(LectureMaterial)
        .where(LectureMaterial.department_id == department_id)
        .where(LectureMaterial.grade_level == grade_level)
        .order_by(LectureMaterial.created_at.desc())
        .limit(20)
    ).all()

    return templates.TemplateResponse(
        "teacher_dashboard.html",
        {
            "request": request,
            "user": user,
            "departments": departments,
            "department_id": department_id,
            "grade_level": grade_level,
            "config": config,
            "defaults": settings,
            "lectures": lectures,
        },
    )


@router.post("/config")
def save_config(
    request: Request,
    department_id: int = Form(...),
    grade_level: int = Form(...),
    max_duration_minutes: int = Form(...),
    max_attempts: int = Form(...),
    max_questions: int = Form(...),
    stop_consecutive_incorrect: int = Form(...),
    stop_slow_seconds: int = Form(...),
    difficulty_min: int = Form(...),
    difficulty_max: int = Form(...),
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    _ensure_department_access(db, user=user, department_id=department_id)
    if grade_level not in {1, 2, 3, 4}:
        raise HTTPException(status_code=400, detail="Invalid grade level.")

    max_duration_minutes = max(1, min(600, int(max_duration_minutes)))
    max_attempts = max(1, min(10, int(max_attempts)))
    max_questions = max(1, min(200, int(max_questions)))
    stop_consecutive_incorrect = max(1, min(50, int(stop_consecutive_incorrect)))
    stop_slow_seconds = max(10, min(7200, int(stop_slow_seconds)))
    difficulty_min = max(1, min(5, int(difficulty_min)))
    difficulty_max = max(1, min(5, int(difficulty_max)))
    if difficulty_min > difficulty_max:
        difficulty_min, difficulty_max = difficulty_max, difficulty_min
    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == department_id)
        .where(ExamConfig.grade_level == grade_level)
    )
    if not cfg:
        cfg = ExamConfig(
            department_id=department_id,
            grade_level=grade_level,
            max_duration_minutes=max_duration_minutes,
            max_attempts=max_attempts,
            max_questions=max_questions,
            stop_consecutive_incorrect=stop_consecutive_incorrect,
            stop_slow_seconds=stop_slow_seconds,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
        )
        db.add(cfg)
    else:
        cfg.max_duration_minutes = max_duration_minutes
        cfg.max_attempts = max_attempts
        cfg.max_questions = max_questions
        cfg.stop_consecutive_incorrect = stop_consecutive_incorrect
        cfg.stop_slow_seconds = stop_slow_seconds
        cfg.difficulty_min = difficulty_min
        cfg.difficulty_max = difficulty_max
        cfg.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(
        f"/teacher?department_id={department_id}&grade_level={grade_level}", status_code=303
    )


@router.post("/lectures/upload")
def upload_lecture(
    request: Request,
    department_id: int = Form(...),
    grade_level: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    settings.ensure_dirs()
    _ensure_department_access(db, user=user, department_id=department_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    contents = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {settings.max_upload_mb} MB).")

    safe_name = os.path.basename(file.filename)
    ext = Path(safe_name).suffix.lower()
    stored_name = f"{uuid4().hex}{ext}"
    out_dir = settings.upload_dir / str(department_id) / str(grade_level)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / stored_name
    out_path.write_bytes(contents)

    try:
        extracted = extract_text_from_upload(out_path)
        if not extracted.strip():
            raise RuntimeError(
                "Could not extract any text from this file. Try a text-based PDF, or install OCR for images/scans."
            )
    except RuntimeError as exc:
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    material = LectureMaterial(
        department_id=department_id,
        grade_level=grade_level,
        uploaded_by_user_id=user.id,
        original_filename=safe_name,
        stored_path=str(out_path),
        file_type=ext.lstrip(".") or "unknown",
        extracted_text=extracted,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    chunks = chunk_text(
        extracted,
        chunk_size=settings.chunk_size_chars,
        overlap=settings.chunk_overlap_chars,
    )
    chunk_rows: list[LectureChunk] = []
    for idx, text in enumerate(chunks):
        chunk_rows.append(
            LectureChunk(
                material_id=material.id,
                department_id=department_id,
                grade_level=grade_level,
                chunk_index=idx,
                text=text,
            )
        )
    db.add_all(chunk_rows)
    db.commit()

    ensure_chunk_embeddings(db, chunk_ids=[c.id for c in chunk_rows], dim=settings.embedding_dim)

    return RedirectResponse(
        f"/teacher?department_id={department_id}&grade_level={grade_level}", status_code=303
    )


@router.get("/results")
def results(
    request: Request,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    departments = _accessible_departments(db, user)
    if not departments:
        raise HTTPException(status_code=403, detail="No departments assigned.")

    department_id = int(request.query_params.get("department_id", departments[0].id))
    grade_level = int(request.query_params.get("grade_level", 1))

    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == department_id)
        .where(ExamConfig.grade_level == grade_level)
    )
    attempts: list[ExamAttempt] = []
    if cfg:
        attempts = db.scalars(
            select(ExamAttempt)
            .where(ExamAttempt.exam_config_id == cfg.id)
            .order_by(ExamAttempt.created_at.desc())
            .limit(100)
        ).all()

    return templates.TemplateResponse(
        "teacher_results.html",
        {
            "request": request,
            "user": user,
            "departments": departments,
            "department_id": department_id,
            "grade_level": grade_level,
            "config": cfg,
            "attempts": attempts,
        },
    )
