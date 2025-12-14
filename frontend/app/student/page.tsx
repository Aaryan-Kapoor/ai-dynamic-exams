"use client";

import { useStudentState, startExam } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
    BookOpen,
    Clock,
    AlertCircle,
    CheckCircle2,
    History,
    PlayCircle,
    BarChart3
} from "lucide-react";
import Link from "next/link";

export default function StudentDashboard() {
    const { state, isLoading, isError } = useStudentState();
    const router = useRouter();
    const [starting, setStarting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleStartExam = async () => {
        setStarting(true);
        setError(null);
        try {
            if (state?.active_attempt) {
                router.push("/student/exam");
                return;
            }
            await startExam();
            router.push("/student/exam");
        } catch (err: any) {
            setError(err.detail || "Failed to start exam.");
            setStarting(false);
        }
    };

    if (isLoading) return <div className="min-h-screen flex items-center justify-center text-zinc-500">Loading student profile...</div>;
    if (isError) return <div className="min-h-screen flex items-center justify-center text-red-500">Error loading profile. Please log in again.</div>;

    const config = state?.config;
    const activeAttempt = state?.active_attempt;
    const attemptsLeft = config ? config.max_attempts - state.attempts_used : 0;

    return (
        <div className="min-h-screen bg-zinc-50 pb-20">
            {/* Header */}
            <header className="bg-white border-b border-zinc-200">
                <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-zinc-900 rounded-lg flex items-center justify-center text-white">
                            <BookOpen size={16} />
                        </div>
                        <span className="font-semibold text-zinc-900">Student Portal</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-zinc-500">Welcome back</span>
                        <div className="w-8 h-8 rounded-full bg-zinc-100 border border-zinc-200"></div>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-6 py-12">
                <div className="mb-10">
                    <h1 className="text-3xl font-serif font-bold text-zinc-900 mb-2">My Examinations</h1>
                    <p className="text-zinc-500">View your assigned evaluations and performance history.</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 flex items-center gap-3">
                        <AlertCircle size={20} />
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Active Exam Card */}
                    <div className="bg-white rounded-2xl shadow-sm border border-zinc-200 p-8 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <BookOpen size={120} />
                        </div>

                        <div className="relative z-10">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-xs font-semibold mb-6">
                                {activeAttempt ? "IN PROGRESS" : "AVAILABLE"}
                            </div>

                            <h2 className="text-2xl font-semibold text-zinc-900 mb-2">
                                {config ? `Department Exam (Grade ${config.grade_level})` : "No Exam Configured"}
                            </h2>

                            <div className="space-y-4 my-8">
                                <div className="flex items-center gap-3 text-sm text-zinc-600">
                                    <Clock size={18} className="text-zinc-400" />
                                    <span>Duration: <strong className="text-zinc-900">{config?.max_duration_minutes || 0} mins</strong></span>
                                </div>
                                <div className="flex items-center gap-3 text-sm text-zinc-600">
                                    <BarChart3 size={18} className="text-zinc-400" />
                                    <span>Attempts Remaining: <strong className="text-zinc-900">{attemptsLeft}</strong> / {config?.max_attempts || 0}</span>
                                </div>
                            </div>

                            {activeAttempt ? (
                                <button
                                    onClick={() => router.push("/student/exam")}
                                    className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-medium shadow-lg shadow-amber-200 transition-all flex items-center justify-center gap-2"
                                >
                                    <PlayCircle size={20} />
                                    Resume Exam
                                </button>
                            ) : (
                                <button
                                    onClick={handleStartExam}
                                    disabled={starting || !config || attemptsLeft <= 0}
                                    className={`w-full py-3 rounded-xl font-medium shadow-lg transition-all flex items-center justify-center gap-2
                                ${(!config || attemptsLeft <= 0)
                                            ? "bg-zinc-100 text-zinc-400 cursor-not-allowed shadow-none"
                                            : "bg-zinc-900 hover:bg-black text-white shadow-zinc-200"
                                        }`}
                                >
                                    {starting ? "Starting..." : "Start New Attempt"}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Performance Summary (Placeholder) */}
                    <div className="bg-zinc-50 rounded-2xl border border-zinc-200 border-dashed p-8 flex flex-col items-center justify-center text-center">
                        <div className="w-16 h-16 bg-zinc-100 rounded-full flex items-center justify-center text-zinc-400 mb-4">
                            <History size={32} />
                        </div>
                        <h3 className="text-lg font-medium text-zinc-900 mb-1">Attempt History</h3>
                        <p className="text-sm text-zinc-500 max-w-xs mx-auto">
                            You have used <strong className="text-zinc-900">{state?.attempts_used}</strong> attempts so far. Complete an exam to see detailed analytics here.
                        </p>
                        <button className="mt-6 text-sm font-medium text-primary-700 hover:text-primary-800">
                            View All Results &rarr;
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}
