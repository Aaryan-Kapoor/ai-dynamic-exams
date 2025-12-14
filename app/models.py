from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    head = "head"
    college_admin = "college_admin"
    system_admin = "system_admin"


class AttemptEndReason(str, enum.Enum):
    completed = "completed"
    student_end = "student_end"
    time_limit = "time_limit"
    too_many_incorrect = "too_many_incorrect"
    too_slow = "too_slow"
    no_questions = "no_questions"
    error = "error"


class QualitativeRating(str, enum.Enum):
    very_good = "very_good"
    good = "good"
    needs_improvement = "needs_improvement"
    bad = "bad"


user_departments = Table(
    "user_departments",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("department_id", ForeignKey("departments.id"), primary_key=True),
)


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="college")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    college: Mapped["College"] = relationship(back_populates="departments")
    users: Mapped[list["User"]] = relationship(
        secondary=user_departments, back_populates="departments"
    )

    __table_args__ = (
        UniqueConstraint("college_id", "name", name="uq_department_college_name"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    university_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), index=True)

    college_id: Mapped[int | None] = mapped_column(ForeignKey("colleges.id"), nullable=True)
    grade_level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # students: 1-4

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    college: Mapped["College"] = relationship()
    departments: Mapped[list["Department"]] = relationship(
        secondary=user_departments, back_populates="users"
    )


class ExamConfig(Base):
    __tablename__ = "exam_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    grade_level: Mapped[int] = mapped_column(Integer, index=True)

    max_duration_minutes: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer)
    max_questions: Mapped[int] = mapped_column(Integer)

    stop_consecutive_incorrect: Mapped[int] = mapped_column(Integer)
    stop_slow_seconds: Mapped[int] = mapped_column(Integer)

    difficulty_min: Mapped[int] = mapped_column(Integer, default=2)
    difficulty_max: Mapped[int] = mapped_column(Integer, default=4)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    department: Mapped["Department"] = relationship()

    __table_args__ = (
        UniqueConstraint("department_id", "grade_level", name="uq_examconfig_dept_grade"),
    )


class LectureMaterial(Base):
    __tablename__ = "lecture_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    grade_level: Mapped[int] = mapped_column(Integer, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(1024))
    file_type: Mapped[str] = mapped_column(String(50))
    extracted_text: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    department: Mapped["Department"] = relationship()
    uploader: Mapped["User"] = relationship()
    chunks: Mapped[list["LectureChunk"]] = relationship(back_populates="material")


class LectureChunk(Base):
    __tablename__ = "lecture_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("lecture_materials.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    grade_level: Mapped[int] = mapped_column(Integer, index=True)

    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    material: Mapped["LectureMaterial"] = relationship(back_populates="chunks")
    embedding: Mapped["LectureChunkEmbedding"] = relationship(
        back_populates="chunk", uselist=False
    )

    __table_args__ = (
        UniqueConstraint("material_id", "chunk_index", name="uq_chunk_material_index"),
    )


class LectureChunkEmbedding(Base):
    __tablename__ = "lecture_chunk_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("lecture_chunks.id"), unique=True, index=True
    )
    embedding_dim: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chunk: Mapped["LectureChunk"] = relationship(back_populates="embedding")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_config_id: Mapped[int] = mapped_column(ForeignKey("exam_configs.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_reason: Mapped[AttemptEndReason | None] = mapped_column(
        Enum(AttemptEndReason), nullable=True
    )
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    correctness_sum: Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_incorrect: Mapped[int] = mapped_column(Integer, default=0)
    max_consecutive_incorrect: Mapped[int] = mapped_column(Integer, default=0)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[QualitativeRating | None] = mapped_column(Enum(QualitativeRating), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exam_config: Mapped["ExamConfig"] = relationship()
    student: Mapped["User"] = relationship()
    questions: Mapped[list["ExamQuestion"]] = relationship(back_populates="attempt")

    __table_args__ = (
        UniqueConstraint(
            "exam_config_id", "student_id", "attempt_number", name="uq_attempt_unique"
        ),
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.id"), index=True)
    question_number: Mapped[int] = mapped_column(Integer)

    question_text: Mapped[str] = mapped_column(Text)
    ideal_answer: Mapped[str] = mapped_column(Text, default="")
    context_text: Mapped[str] = mapped_column(Text, default="")

    shown_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attempt: Mapped["ExamAttempt"] = relationship(back_populates="questions")
    answer: Mapped["ExamAnswer"] = relationship(back_populates="question", uselist=False)

    __table_args__ = (
        UniqueConstraint("attempt_id", "question_number", name="uq_question_attempt_number"),
    )


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("exam_questions.id"), unique=True, index=True
    )

    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)

    student_answer: Mapped[str] = mapped_column(Text, default="")
    correctness: Mapped[float] = mapped_column(Float, default=0.0)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str] = mapped_column(Text, default="")

    question: Mapped["ExamQuestion"] = relationship(back_populates="answer")
