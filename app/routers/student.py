from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    AttemptEndReason,
    Department,
    ExamAttempt,
    ExamConfig,
    ExamQuestion,
    Role,
    User,
)
from app.rbac import require_roles
from app.services.exam_logic import (
    attempt_elapsed_seconds,
    compute_score_and_rating,
    finalize_attempt,
    generate_next_question,
    get_active_attempt,
    should_auto_end_after_answer,
)
from app.services.llm import FallbackLLMClient, MockLLMClient, OpenAICompatLLMClient


router = APIRouter(prefix="/student", tags=["student"])
templates = Jinja2Templates(directory="app/templates")


def _get_llm(settings):
    if settings.llm_provider == "mock":
        return MockLLMClient()
    primary = OpenAICompatLLMClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    if settings.llm_fallback_to_mock:
        return FallbackLLMClient(primary=primary, fallback=MockLLMClient())
    return primary


def _time_limit_seconds(cfg: ExamConfig) -> int:
    return int(cfg.max_duration_minutes) * 60


def _is_time_up(cfg: ExamConfig, *, elapsed_seconds: int) -> bool:
    return elapsed_seconds >= _time_limit_seconds(cfg)


def _get_student_department_and_grade(student: User) -> tuple[int, int]:
    if not student.departments:
        raise HTTPException(status_code=400, detail="Student has no department assigned.")
    if not student.grade_level:
        raise HTTPException(status_code=400, detail="Student has no grade level assigned.")
    # For simplicity, student uses first department.
    return student.departments[0].id, int(student.grade_level)


@router.get("")
def student_home(
    request: Request,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)

    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == dept_id)
        .where(ExamConfig.grade_level == grade)
        .where(ExamConfig.active.is_(True))
    )

    active_attempt = cfg and get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    attempts_used = cfg and (
        db.scalar(
            select(ExamAttempt.attempt_number)
            .where(ExamAttempt.student_id == student.id)
            .where(ExamAttempt.exam_config_id == cfg.id)
            .order_by(ExamAttempt.attempt_number.desc())
        )
        or 0
    )

    return templates.TemplateResponse(
        "student_home.html",
        {
            "request": request,
            "student": student,
            "config": cfg,
            "active_attempt": active_attempt,
            "attempts_used": attempts_used,
            "max_attempts": cfg.max_attempts if cfg else 0,
        },
    )


@router.post("/exam/start")
def start_exam(
    request: Request,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)

    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == dept_id)
        .where(ExamConfig.grade_level == grade)
        .where(ExamConfig.active.is_(True))
    )
    if not cfg:
        raise HTTPException(status_code=400, detail="No exam configured for your department/grade yet.")

    active = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    if active:
        return RedirectResponse("/student/exam", status_code=303)

    attempts_total = (
        db.scalar(
            select(ExamAttempt.attempt_number)
            .where(ExamAttempt.student_id == student.id)
            .where(ExamAttempt.exam_config_id == cfg.id)
            .order_by(ExamAttempt.attempt_number.desc())
        )
        or 0
    )
    next_no = int(attempts_total) + 1
    if next_no > cfg.max_attempts:
        raise HTTPException(status_code=400, detail="No attempts left.")

    attempt = ExamAttempt(exam_config_id=cfg.id, student_id=student.id, attempt_number=next_no)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    llm = _get_llm(settings)
    q = generate_next_question(
        db,
        settings=settings,
        llm=llm,
        attempt=attempt,
        config=cfg,
        department_id=dept_id,
        grade_level=grade,
    )
    if not q:
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.no_questions)
        return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)

    return RedirectResponse("/student/exam", status_code=303)


@router.get("/exam")
def exam_page(
    request: Request,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)

    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == dept_id)
        .where(ExamConfig.grade_level == grade)
        .where(ExamConfig.active.is_(True))
    )
    if not cfg:
        return RedirectResponse("/student", status_code=303)

    attempt = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    if not attempt:
        return RedirectResponse("/student", status_code=303)

    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    if _is_time_up(cfg, elapsed_seconds=elapsed):
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.time_limit)
        return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)

    question = db.scalar(
        select(ExamQuestion)
        .where(ExamQuestion.attempt_id == attempt.id)
        .order_by(ExamQuestion.question_number.desc())
    )
    if not question or question.answer is not None:
        return RedirectResponse("/student", status_code=303)

    avg_time_per_q = elapsed / max(1, attempt.questions_answered)
    score_so_far, rating_so_far = compute_score_and_rating(
        settings=settings, attempt=attempt, config=cfg, avg_time_per_q=avg_time_per_q
    )
    score_so_far = max(0.0, min(100.0, score_so_far))

    return templates.TemplateResponse(
        "student_exam.html",
        {
            "request": request,
            "student": student,
            "config": cfg,
            "attempt": attempt,
            "question": question,
            "elapsed_seconds": elapsed,
            "score_so_far": score_so_far,
            "rating_so_far": rating_so_far.value,
        },
    )


@router.post("/exam/answer")
def submit_answer(
    request: Request,
    question_id: int = Form(...),
    student_answer: str = Form(""),
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)

    question = db.scalar(select(ExamQuestion).where(ExamQuestion.id == question_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    attempt = question.attempt
    cfg = attempt.exam_config
    if attempt.student_id != student.id or attempt.ended_at is not None:
        raise HTTPException(status_code=400, detail="Attempt not active.")
    if question.answer is not None:
        return RedirectResponse("/student/exam", status_code=303)

    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    if _is_time_up(cfg, elapsed_seconds=elapsed):
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.time_limit)
        return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)

    llm = _get_llm(settings)

    from app.services.exam_logic import grade_and_record_answer

    graded = grade_and_record_answer(db, llm=llm, attempt=attempt, question=question, student_answer=student_answer)

    last_time = question.answer.time_taken_seconds if question.answer else 0
    end_reason = should_auto_end_after_answer(
        attempt=attempt,
        config=cfg,
        last_time_taken_seconds=last_time,
    )

    if end_reason:
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=end_reason)
        return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)

    next_q = generate_next_question(
        db,
        settings=settings,
        llm=llm,
        attempt=attempt,
        config=cfg,
        department_id=dept_id,
        grade_level=grade,
    )
    if not next_q:
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.no_questions)
        return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)

    return RedirectResponse("/student/exam", status_code=303)


@router.post("/exam/end")
def end_exam(
    request: Request,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)
    cfg = db.scalar(
        select(ExamConfig)
        .where(ExamConfig.department_id == dept_id)
        .where(ExamConfig.grade_level == grade)
        .where(ExamConfig.active.is_(True))
    )
    if not cfg:
        return RedirectResponse("/student", status_code=303)
    attempt = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    if not attempt:
        return RedirectResponse("/student", status_code=303)
    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    reason = AttemptEndReason.time_limit if _is_time_up(cfg, elapsed_seconds=elapsed) else AttemptEndReason.student_end
    finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=reason)
    return RedirectResponse(f"/student/results/{attempt.id}", status_code=303)


@router.get("/results/{attempt_id}")
def results_page(
    request: Request,
    attempt_id: int,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    if not attempt or attempt.student_id != student.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    cfg = attempt.exam_config
    used = (
        db.scalar(
            select(ExamAttempt.attempt_number)
            .where(ExamAttempt.student_id == student.id)
            .where(ExamAttempt.exam_config_id == cfg.id)
            .order_by(ExamAttempt.attempt_number.desc())
        )
        or 0
    )
    attempts_left = max(0, cfg.max_attempts - int(used))

    return templates.TemplateResponse(
        "student_results.html",
        {
            "request": request,
            "student": student,
            "attempt": attempt,
            "attempts_left": attempts_left,
        },
    )
