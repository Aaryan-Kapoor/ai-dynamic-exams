from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models import Role, AttemptEndReason, QualitativeRating

class DepartmentRead(BaseModel):
    id: int
    name: str
    college_id: int
    model_config = ConfigDict(from_attributes=True)

class CollegeRead(BaseModel):
    id: int
    name: str
    departments: List[DepartmentRead] = []
    model_config = ConfigDict(from_attributes=True)

class UserRead(BaseModel):
    id: int
    university_id: str
    full_name: str
    role: Role
    college_id: Optional[int] = None
    grade_level: Optional[int] = None
    is_active: bool
    departments: List[DepartmentRead] = []
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    university_id: str
    password: str

class ExamConfigRead(BaseModel):
    id: int
    department_id: int
    grade_level: int
    max_duration_minutes: int
    max_attempts: int
    max_questions: int
    stop_consecutive_incorrect: int
    stop_slow_seconds: int
    difficulty_min: int
    difficulty_max: int
    active: bool
    model_config = ConfigDict(from_attributes=True)

class ExamConfigUpdate(BaseModel):
    department_id: int
    grade_level: int
    max_duration_minutes: int
    max_attempts: int
    max_questions: int
    stop_consecutive_incorrect: int
    stop_slow_seconds: int
    difficulty_min: int
    difficulty_max: int

class LectureMaterialRead(BaseModel):
    id: int
    department_id: int
    grade_level: int
    original_filename: str
    file_type: str
    extracted_text: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ExamAttemptRead(BaseModel):
    id: int
    exam_config_id: int
    student_id: int
    attempt_number: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    ended_reason: Optional[AttemptEndReason] = None
    elapsed_seconds: Optional[int] = None
    questions_answered: int
    score: Optional[float] = None
    rating: Optional[QualitativeRating] = None
    model_config = ConfigDict(from_attributes=True)

class ExamQuestionRead(BaseModel):
    id: int
    question_number: int
    question_text: str
    model_config = ConfigDict(from_attributes=True)

class AnswerSubmit(BaseModel):
    question_id: int
    student_answer: str

class AnswerFeedback(BaseModel):
    correctness: float
    is_correct: bool
    feedback: str
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    university_id: str
    password: str
    full_name: str
    role: Role
    college_id: Optional[int] = None
    grade_level: Optional[int] = None

class StudentExamState(BaseModel):
    config: Optional[ExamConfigRead] = None
    active_attempt: Optional[ExamAttemptRead] = None
    attempts_used: int
    max_attempts: int

class ActiveExamState(BaseModel):
    attempt: ExamAttemptRead
    question: Optional[ExamQuestionRead] = None
    elapsed_seconds: int
    score_so_far: float
    rating_so_far: Optional[str] = None
    time_remaining_seconds: int

class AnswerResponse(BaseModel):
    feedback: AnswerFeedback
    next_action: str  # "continue" or "ended"
    end_reason: Optional[AttemptEndReason] = None
    next_question: Optional[ExamQuestionRead] = None  # Include next question directly

class TeacherDashboardState(BaseModel):
    departments: List[DepartmentRead]
    current_department_id: int
    current_grade_level: int
    config: Optional[ExamConfigRead]
    lectures: List[LectureMaterialRead]
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Role] = None
    college_id: Optional[int] = None
    grade_level: Optional[int] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    department_ids: Optional[List[int]] = None

class CollegeCreate(BaseModel):
    name: str

class DepartmentCreate(BaseModel):
    name: str
    college_id: int
