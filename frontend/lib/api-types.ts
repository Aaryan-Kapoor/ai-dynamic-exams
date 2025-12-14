export enum Role {
    student = "student",
    teacher = "teacher",
    head = "head",
    college_admin = "college_admin",
    system_admin = "system_admin",
}

export enum AttemptEndReason {
    completed = "completed",
    student_end = "student_end",
    time_limit = "time_limit",
    too_many_incorrect = "too_many_incorrect",
    too_slow = "too_slow",
    no_questions = "no_questions",
    error = "error",
}

export interface Department {
    id: number;
    name: string;
    college_id: number;
}

export interface User {
    id: number;
    university_id: string;
    full_name: string;
    role: Role;
    college_id?: number;
    grade_level?: number;
    is_active: boolean;
    departments: Department[];
}

export interface ExamConfig {
    id: number;
    department_id: number;
    grade_level: number;
    max_duration_minutes: number;
    max_attempts: number;
    max_questions: number;
    stop_consecutive_incorrect: number;
    stop_slow_seconds: number;
    difficulty_min: number;
    difficulty_max: number;
    active: boolean;
}

export interface LectureMaterial {
    id: number;
    department_id: number;
    grade_level: number;
    original_filename: string;
    file_type: string;
    extracted_text?: string;
    created_at: string;
}

export interface ExamAttempt {
    id: number;
    exam_config_id: number;
    student_id: number;
    attempt_number: number;
    started_at: string;
    ended_at?: string;
    ended_reason?: AttemptEndReason;
    elapsed_seconds?: number;
    questions_answered: number;
    score?: number;
    rating?: string;
}

export interface ExamQuestion {
    id: number;
    question_number: number;
    question_text: string;
}

export interface AnswerFeedback {
    correctness: number;
    is_correct: boolean;
    feedback: string;
}

export interface ActiveExamState {
    attempt: ExamAttempt;
    question?: ExamQuestion;
    elapsed_seconds: number;
    score_so_far: number;
    rating_so_far?: string;
    time_remaining_seconds: number;
}

export interface AnswerResponse {
    feedback: AnswerFeedback;
    next_action: "continue" | "ended";
    end_reason?: AttemptEndReason;
    next_question?: ExamQuestion;
}

export interface StudentExamState {
    config?: ExamConfig;
    active_attempt?: ExamAttempt;
    attempts_used: number;
    max_attempts: number;
}

export interface TeacherDashboardState {
    departments: Department[];
    current_department_id: number;
    current_grade_level: number;
    config?: ExamConfig;
    lectures: LectureMaterial[];
}
