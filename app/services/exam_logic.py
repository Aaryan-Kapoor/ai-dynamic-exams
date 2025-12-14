from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    AttemptEndReason,
    ExamAttempt,
    ExamAnswer,
    ExamConfig,
    ExamQuestion,
    QualitativeRating,
)
from app.services.llm import GradedAnswer, LLMClient
from app.services.vector_index import query_similar_chunks


def _rating_from_score(score: float) -> QualitativeRating:
    if score >= 85:
        return QualitativeRating.very_good
    if score >= 70:
        return QualitativeRating.good
    if score >= 50:
        return QualitativeRating.needs_improvement
    return QualitativeRating.bad


def compute_score_and_rating(
    *,
    settings: Settings,
    attempt: ExamAttempt,
    config: ExamConfig,
    avg_time_per_q: float,
) -> tuple[float, QualitativeRating]:
    answered = max(1, attempt.questions_answered)
    correctness_avg = attempt.correctness_sum / answered

    slow = max(10, config.stop_slow_seconds)
    speed_score = max(0.0, min(1.0, 1.0 - (avg_time_per_q / slow)))

    denom = max(1, config.stop_consecutive_incorrect)
    consistency_score = max(0.0, min(1.0, 1.0 - (attempt.max_consecutive_incorrect / denom)))

    w1 = settings.score_weight_correctness
    w2 = settings.score_weight_speed
    w3 = settings.score_weight_consistency
    total_w = (w1 + w2 + w3) or 1.0
    w1, w2, w3 = w1 / total_w, w2 / total_w, w3 / total_w

    score = 100.0 * (w1 * correctness_avg + w2 * speed_score + w3 * consistency_score)
    rating = _rating_from_score(score)
    return score, rating


def attempt_elapsed_seconds(attempt: ExamAttempt, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    delta = now - attempt.started_at
    return max(0, int(delta.total_seconds()))


def has_time_left(config: ExamConfig, *, elapsed_seconds: int) -> bool:
    return elapsed_seconds < (config.max_duration_minutes * 60)


def get_active_attempt(
    db: Session, *, student_id: int, exam_config_id: int
) -> ExamAttempt | None:
    return db.scalar(
        select(ExamAttempt)
        .where(ExamAttempt.student_id == student_id)
        .where(ExamAttempt.exam_config_id == exam_config_id)
        .where(ExamAttempt.ended_at.is_(None))
        .order_by(ExamAttempt.started_at.desc())
    )


def count_attempts(db: Session, *, student_id: int, exam_config_id: int) -> int:
    return (
        db.scalar(
            select(func.count(ExamAttempt.id))
            .where(ExamAttempt.student_id == student_id)
            .where(ExamAttempt.exam_config_id == exam_config_id)
        )
        or 0
    )


def list_previous_questions(
    db: Session, *, student_id: int, exam_config_id: int, limit: int = 100
) -> list[str]:
    rows = db.execute(
        select(ExamQuestion.question_text)
        .join(ExamAttempt, ExamAttempt.id == ExamQuestion.attempt_id)
        .where(ExamAttempt.student_id == student_id)
        .where(ExamAttempt.exam_config_id == exam_config_id)
        .order_by(ExamQuestion.created_at.desc())
        .limit(limit)
    ).all()
    return [r[0] for r in rows]


def _hash_question(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def generate_next_question(
    db: Session,
    *,
    settings: Settings,
    llm: LLMClient,
    attempt: ExamAttempt,
    config: ExamConfig,
    department_id: int,
    grade_level: int,
) -> ExamQuestion | None:
    asked = [q.question_text for q in attempt.questions]
    avoid = list_previous_questions(db, student_id=attempt.student_id, exam_config_id=config.id)
    avoid_hashes = {_hash_question(q) for q in avoid}

    difficulty = random.randint(config.difficulty_min, config.difficulty_max)
    query = asked[-1] if asked else "Important lecture concepts and definitions"
    chunks = query_similar_chunks(
        db,
        query=query,
        department_id=department_id,
        grade_level=grade_level,
        limit=settings.context_chunks,
        dim=settings.embedding_dim,
    )
    context_text = "\n\n---\n\n".join(c.text for c in chunks)[: settings.max_context_chars]

    if not context_text.strip():
        return None

    for _ in range(3):
        gen = llm.generate_question(context=context_text, difficulty=difficulty, avoid_questions=avoid)
        if _hash_question(gen.question) not in avoid_hashes:
            break
        difficulty = random.randint(config.difficulty_min, config.difficulty_max)

    question_number = (max((q.question_number for q in attempt.questions), default=0) + 1)
    q = ExamQuestion(
        attempt_id=attempt.id,
        question_number=question_number,
        question_text=gen.question.strip(),
        ideal_answer=gen.ideal_answer.strip(),
        context_text=context_text.strip(),
        shown_at=datetime.utcnow(),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def grade_and_record_answer(
    db: Session,
    *,
    llm: LLMClient,
    attempt: ExamAttempt,
    question: ExamQuestion,
    student_answer: str,
) -> GradedAnswer:
    now = datetime.utcnow()
    time_taken = max(0, int((now - question.shown_at).total_seconds()))

    graded = llm.grade_answer(
        question=question.question_text,
        ideal_answer=question.ideal_answer,
        context=question.context_text,
        student_answer=student_answer,
    )

    db.add(
        ExamAnswer(
            question_id=question.id,
            answered_at=now,
            time_taken_seconds=time_taken,
            student_answer=student_answer,
            correctness=graded.correctness,
            is_correct=graded.is_correct,
            feedback=graded.feedback,
        )
    )

    attempt.questions_answered += 1
    attempt.correctness_sum += graded.correctness

    if graded.is_correct:
        attempt.consecutive_incorrect = 0
    else:
        attempt.consecutive_incorrect += 1
        attempt.max_consecutive_incorrect = max(
            attempt.max_consecutive_incorrect, attempt.consecutive_incorrect
        )

    db.commit()
    return graded


def finalize_attempt(
    db: Session,
    *,
    settings: Settings,
    attempt: ExamAttempt,
    config: ExamConfig,
    reason: AttemptEndReason,
) -> None:
    now = datetime.utcnow()
    attempt.ended_at = now
    attempt.ended_reason = reason
    attempt.elapsed_seconds = attempt_elapsed_seconds(attempt, now=now)

    times = db.scalars(
        select(ExamAnswer.time_taken_seconds)
        .join(ExamQuestion, ExamQuestion.id == ExamAnswer.question_id)
        .where(ExamQuestion.attempt_id == attempt.id)
    ).all()
    avg_time = (sum(times) / max(1, len(times))) if times else 0.0

    score, rating = compute_score_and_rating(
        settings=settings, attempt=attempt, config=config, avg_time_per_q=avg_time
    )
    attempt.score = score
    attempt.rating = rating
    db.commit()


def should_auto_end_after_answer(
    *,
    attempt: ExamAttempt,
    config: ExamConfig,
    last_time_taken_seconds: int,
) -> AttemptEndReason | None:
    if attempt.questions_answered >= config.max_questions:
        return AttemptEndReason.completed
    if attempt.consecutive_incorrect >= config.stop_consecutive_incorrect:
        return AttemptEndReason.too_many_incorrect
    if last_time_taken_seconds >= config.stop_slow_seconds:
        return AttemptEndReason.too_slow
    elapsed = attempt_elapsed_seconds(attempt)
    if elapsed >= config.max_duration_minutes * 60:
        return AttemptEndReason.time_limit
    return None

