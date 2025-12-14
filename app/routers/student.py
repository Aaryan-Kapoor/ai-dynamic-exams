from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    AttemptEndReason,
    ExamAttempt,
    ExamConfig,
    ExamQuestion,
    Role,
    User,
)
from app.rbac import require_roles
from app.schemas import (
    ActiveExamState,
    AnswerFeedback,
    AnswerResponse,
    AnswerSubmit,
    ExamAttemptRead,
    ExamConfigRead,
    ExamQuestionRead,
    StudentExamState,
)
from app.services.exam_logic import (
    attempt_elapsed_seconds,
    compute_score_and_rating,
    finalize_attempt,
    generate_next_question,
    get_active_attempt,
    should_auto_end_after_answer,
    grade_and_record_answer,
)
from app.services.llm import FallbackLLMClient, MockLLMClient, OpenAICompatLLMClient


router = APIRouter(prefix="/student", tags=["student"])


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


@router.get("/state", response_model=StudentExamState)
def student_state(
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

    active_attempt = None
    if cfg:
        active_attempt = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    
    attempts_used = 0
    if cfg:
        attempts_used = (
            db.scalar(
                select(ExamAttempt.attempt_number)
                .where(ExamAttempt.student_id == student.id)
                .where(ExamAttempt.exam_config_id == cfg.id)
                .order_by(ExamAttempt.attempt_number.desc())
            )
            or 0
        )

    return StudentExamState(
        config=cfg,
        active_attempt=active_attempt,
        attempts_used=attempts_used,
        max_attempts=cfg.max_attempts if cfg else 0,
    )


@router.post("/exam/start", response_model=ExamAttemptRead)
def start_exam(
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
        raise HTTPException(status_code=400, detail="An exam attempt is already active.")

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
        raise HTTPException(status_code=400, detail="Could not generate questions. Exam ended.")

    return attempt


@router.get("/exam/active", response_model=ActiveExamState)
def get_active_exam_data(
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
         raise HTTPException(status_code=404, detail="No active exam config.")

    attempt = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    if not attempt:
         raise HTTPException(status_code=404, detail="No active attempt.")

    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    if _is_time_up(cfg, elapsed_seconds=elapsed):
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.time_limit)
        raise HTTPException(status_code=409, detail="Time limit reached.")

    question = db.scalar(
        select(ExamQuestion)
        .where(ExamQuestion.attempt_id == attempt.id)
        .order_by(ExamQuestion.question_number.desc())
    )
    
    # Don't return the question if it's already answered, waiting for next generation or end
    if question and question.answer is not None:
        question = None

    avg_time_per_q = elapsed / max(1, attempt.questions_answered)
    score_so_far, rating_so_far = compute_score_and_rating(
        settings=settings, attempt=attempt, config=cfg, avg_time_per_q=avg_time_per_q
    )
    score_so_far = max(0.0, min(100.0, score_so_far))
    
    time_limit = _time_limit_seconds(cfg)
    remaining = max(0, time_limit - elapsed)

    return ActiveExamState(
        attempt=attempt,
        question=question,
        elapsed_seconds=elapsed,
        score_so_far=score_so_far,
        rating_so_far=rating_so_far.value if rating_so_far else None,
        time_remaining_seconds=remaining,
    )


@router.post("/exam/answer", response_model=AnswerResponse)
def submit_answer(
    payload: AnswerSubmit,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    dept_id, grade = _get_student_department_and_grade(student)

    question = db.scalar(select(ExamQuestion).where(ExamQuestion.id == payload.question_id))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    attempt = question.attempt
    cfg = attempt.exam_config
    
    if attempt.student_id != student.id or attempt.ended_at is not None:
        raise HTTPException(status_code=400, detail="Attempt not active.")
    if question.answer is not None:
         raise HTTPException(status_code=400, detail="Question already answered.")

    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    if _is_time_up(cfg, elapsed_seconds=elapsed):
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=AttemptEndReason.time_limit)
        return AnswerResponse(
            feedback=AnswerFeedback(correctness=0, is_correct=False, feedback="Time limit reached."),
            next_action="ended",
            end_reason=AttemptEndReason.time_limit
        )

    llm = _get_llm(settings)

    graded = grade_and_record_answer(
        db, 
        llm=llm, 
        attempt=attempt, 
        question=question, 
        student_answer=payload.student_answer
    )

    last_time = question.answer.time_taken_seconds if question.answer else 0
    end_reason = should_auto_end_after_answer(
        attempt=attempt,
        config=cfg,
        last_time_taken_seconds=last_time,
    )

    response_feedback = AnswerFeedback(
        correctness=graded.correctness,
        is_correct=graded.is_correct,
        feedback=graded.feedback
    )

    if end_reason:
        finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=end_reason)
        return AnswerResponse(
            feedback=response_feedback,
            next_action="ended",
            end_reason=end_reason
        )

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
        return AnswerResponse(
            feedback=response_feedback,
            next_action="ended",
            end_reason=AttemptEndReason.no_questions
        )

    return AnswerResponse(
        feedback=response_feedback,
        next_action="continue",
        next_question=ExamQuestionRead(
            id=next_q.id,
            question_number=next_q.question_number,
            question_text=next_q.question_text,
        )
    )


@router.post("/exam/end", response_model=ExamAttemptRead)
def end_exam(
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
        raise HTTPException(status_code=400, detail="No config found.")
        
    attempt = get_active_attempt(db, student_id=student.id, exam_config_id=cfg.id)
    if not attempt:
        raise HTTPException(status_code=400, detail="No active attempt.")
        
    elapsed = attempt_elapsed_seconds(attempt, now=datetime.utcnow())
    reason = AttemptEndReason.time_limit if _is_time_up(cfg, elapsed_seconds=elapsed) else AttemptEndReason.student_end
    finalize_attempt(db, settings=settings, attempt=attempt, config=cfg, reason=reason)
    return attempt


@router.get("/results/{attempt_id}", response_model=ExamAttemptRead)
def get_results(
    attempt_id: int,
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    if not attempt or attempt.student_id != student.id:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    return attempt

@router.get("/history", response_model=list[ExamAttemptRead])
def get_history(
    student: User = Depends(require_roles(Role.student)),
    db: Session = Depends(get_db),
):
    attempts = db.scalars(
        select(ExamAttempt)
        .where(ExamAttempt.student_id == student.id)
        .order_by(ExamAttempt.created_at.desc())
    ).all()
    return attempts
