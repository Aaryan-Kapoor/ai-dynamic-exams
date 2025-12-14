from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
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
    LectureChunkEmbedding,
    LectureMaterial,
    Role,
    User,
)
from app.rbac import require_roles
from app.schemas import (
    ExamConfigRead,
    ExamConfigUpdate,
    TeacherDashboardState,
    DepartmentRead,
    LectureMaterialRead,
    ExamAttemptRead,
)
from app.services.lecture_processing import chunk_text, extract_text_from_upload
from app.services.vector_index import ensure_chunk_embeddings


router = APIRouter(prefix="/teacher", tags=["teacher"])


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


@router.get("/dashboard", response_model=TeacherDashboardState)
def dashboard(
    department_id: int | None = None,
    grade_level: int = 1,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    departments = _accessible_departments(db, user)
    if not departments:
        raise HTTPException(status_code=403, detail="No departments assigned to this teacher.")

    allowed_ids = {d.id for d in departments}
    
    if department_id is None:
        department_id = departments[0].id
        
    if department_id not in allowed_ids:
        department_id = departments[0].id

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

    return TeacherDashboardState(
        departments=departments,
        current_department_id=department_id,
        current_grade_level=grade_level,
        config=config,
        lectures=lectures,
    )


@router.post("/config", response_model=ExamConfigRead)
def save_config(
    payload: ExamConfigUpdate,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    _ensure_department_access(db, user=user, department_id=payload.department_id)
    if payload.grade_level not in {1, 2, 3, 4}:
        raise HTTPException(status_code=400, detail="Invalid grade level.")

    # Validate ranges
    max_duration_minutes = max(1, min(600, payload.max_duration_minutes))
    max_attempts = max(1, min(10, payload.max_attempts))
    max_questions = max(1, min(200, payload.max_questions))
    stop_consecutive_incorrect = max(1, min(50, payload.stop_consecutive_incorrect))
    stop_slow_seconds = max(10, min(7200, payload.stop_slow_seconds))
    difficulty_min = max(1, min(5, payload.difficulty_min))
    difficulty_max = max(1, min(5, payload.difficulty_max))
    
    if difficulty_min > difficulty_max:
        difficulty_min, difficulty_max = difficulty_max, difficulty_min

    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == payload.department_id)
        .where(ExamConfig.grade_level == payload.grade_level)
    )
    
    if not cfg:
        cfg = ExamConfig(
            department_id=payload.department_id,
            grade_level=payload.grade_level,
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
    db.refresh(cfg)
    return cfg


@router.post("/lectures/upload", response_model=LectureMaterialRead)
def upload_lecture(
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
                "Could not extract any text from this file. "
                "Try a text-based PDF, or install OCR for images/scans."
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

    return material


@router.delete("/lectures/{lecture_id}")
def delete_lecture(
    lecture_id: int,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    lecture = db.scalar(select(LectureMaterial).where(LectureMaterial.id == lecture_id))
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    _ensure_department_access(db, user=user, department_id=lecture.department_id)

    # Delete from disk
    if lecture.stored_path:
        try:
            p = Path(lecture.stored_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass  # Log error ideally

    # Explicitly delete chunks and their embeddings first
    chunks = db.scalars(select(LectureChunk).where(LectureChunk.material_id == lecture_id)).all()
    for chunk in chunks:
        # Delete embedding if exists
        embedding = db.scalar(select(LectureChunkEmbedding).where(LectureChunkEmbedding.chunk_id == chunk.id))
        if embedding:
            db.delete(embedding)
        db.delete(chunk)
    
    db.delete(lecture)
    db.commit()
    return {"status": "success"}



@router.get("/results", response_model=list[ExamAttemptRead])
def results(
    department_id: int | None = None,
    grade_level: int = 1,
    user: User = Depends(require_roles(Role.teacher, Role.head, Role.college_admin, Role.system_admin)),
    db: Session = Depends(get_db),
):
    departments = _accessible_departments(db, user)
    if not departments:
        raise HTTPException(status_code=403, detail="No departments assigned.")
    
    if department_id is None:
        department_id = departments[0].id
        
    _ensure_department_access(db, user=user, department_id=department_id)

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

    return attempts
