import useSWR from 'swr';
import {
    User,
    StudentExamState,
    ActiveExamState,
    TeacherDashboardState,
    ExamConfig
} from './api-types';

const API_BASE = '/api'; // We will use Next.js rewrites to proxy to backend

export class APIError extends Error {
    info: any;
    status: number;
    constructor(message: string, info: any, status: number) {
        super(message);
        this.info = info;
        this.status = status;
    }
}

export const fetcher = async (url: string) => {
    const res = await fetch(url);
    if (!res.ok) {
        const error = new APIError('An error occurred while fetching the data.', await res.json(), res.status);
        throw error;
    }
    return res.json();
};

export function useUser() {
    const { data, error, mutate } = useSWR<User>('/auth/me', fetcher, {
        shouldRetryOnError: false,
    });
    return {
        user: data,
        isLoading: !error && !data,
        isError: error,
        mutate,
    };
}

export function useStudentState() {
    const { data, error, mutate } = useSWR<StudentExamState>('/student/state', fetcher);
    return {
        state: data,
        isLoading: !error && !data,
        isError: error,
        mutate,
    };
}

export function useActiveExam() {
    const { data, error, mutate } = useSWR<ActiveExamState>('/student/exam/active', fetcher, {
        refreshInterval: 1000, // Poll every second for timer sync if needed, though local timer is better
        revalidateOnFocus: false,
    });
    return {
        examState: data,
        isLoading: !error && !data,
        isError: error,
        mutate,
    };
}

export function useTeacherDashboard(deptId?: number, grade?: number) {
    const params = new URLSearchParams();
    if (deptId) params.append('department_id', deptId.toString());
    if (grade) params.append('grade_level', grade.toString());

    const { data, error, mutate } = useSWR<TeacherDashboardState>(`/teacher/dashboard?${params.toString()}`, fetcher);
    return {
        dashboard: data,
        isLoading: !error && !data,
        isError: error,
        mutate,
    };
}

// POST helpers
export async function login(university_id: string, password: string): Promise<User> {
    const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ university_id, password }),
    });
    if (!res.ok) throw await res.json();
    return res.json();
}

export async function logout() {
    await fetch('/auth/logout', { method: 'POST' });
}

export async function startExam() {
    const res = await fetch('/student/exam/start', { method: 'POST' });
    if (!res.ok) throw await res.json();
    return res.json();
}

export async function submitAnswer(questionId: number, answer: string) {
    const res = await fetch('/student/exam/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId, student_answer: answer }),
    });
    if (!res.ok) throw await res.json();
    return res.json();
}

export async function endExam() {
    const res = await fetch('/student/exam/end', { method: 'POST' });
    if (!res.ok) throw await res.json();
    return res.json();
}

export async function saveExamConfig(config: any) {
    const res = await fetch('/teacher/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    if (!res.ok) throw await res.json();
    return res.json();
}

export async function deleteLecture(id: number) {
    const res = await fetch(`/teacher/lectures/${id}`, {
        method: 'DELETE',
    });
    if (!res.ok) {
        // Try to parse as JSON, fallback to text
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            throw await res.json();
        } else {
            const text = await res.text();
            throw { detail: text || `Error ${res.status}` };
        }
    }
    // Handle empty response (204) or JSON response
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        return res.json();
    }
    return { status: 'success' };
}
