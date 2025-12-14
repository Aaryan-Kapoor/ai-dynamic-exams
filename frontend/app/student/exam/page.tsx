"use client";

import { useActiveExam, submitAnswer, endExam } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import {
    Clock,
    Send,
    CheckCircle,
    AlertTriangle,
    Loader2,
    ArrowRight
} from "lucide-react";
import { AnswerResponse, ExamQuestion } from "@/lib/api-types";

function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function ExamSessionPage() {
    const router = useRouter();
    const { examState, isLoading, isError, mutate } = useActiveExam();

    const [answer, setAnswer] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [feedback, setFeedback] = useState<{ correct: boolean, text: string } | null>(null);

    // Local question state to prevent flashing during transitions
    const [currentQuestion, setCurrentQuestion] = useState<ExamQuestion | null>(null);
    const [questionNumber, setQuestionNumber] = useState(1);

    // Store the pending next question (user must click to continue)
    const [pendingNextQuestion, setPendingNextQuestion] = useState<ExamQuestion | null>(null);

    // Local timer for smooth countdown
    const [timeLeft, setTimeLeft] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    // Track if we're waiting for redirect after exam ends
    const [examEnded, setExamEnded] = useState(false);

    // Sync time from server
    useEffect(() => {
        if (examState?.time_remaining_seconds !== undefined) {
            setTimeLeft(examState.time_remaining_seconds);
        }
    }, [examState?.time_remaining_seconds]);

    // Sync question from server (only when not in feedback state)
    useEffect(() => {
        if (examState?.question && !feedback && !submitting && !pendingNextQuestion) {
            setCurrentQuestion(examState.question);
            setQuestionNumber(examState.attempt.questions_answered + 1);
        }
    }, [examState?.question, feedback, submitting, examState?.attempt?.questions_answered, pendingNextQuestion]);

    // Local countdown timer
    useEffect(() => {
        timerRef.current = setInterval(() => {
            setTimeLeft((t) => {
                if (t <= 0) return 0;
                return t - 1;
            });
        }, 1000);
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, []);

    const handleSubmit = async () => {
        if (!currentQuestion || !answer.trim() || submitting) return;
        setSubmitting(true);
        setFeedback(null);
        setPendingNextQuestion(null);

        try {
            const res: AnswerResponse = await submitAnswer(currentQuestion.id, answer);

            // Show feedback
            setFeedback({
                correct: res.feedback.is_correct,
                text: res.feedback.feedback
            });

            if (res.next_action === "ended") {
                setExamEnded(true);
                setSubmitting(false);
                // Don't auto-redirect, let user see feedback and click View Results
            } else if (res.next_question) {
                // Store the next question, user must click to continue
                setPendingNextQuestion(res.next_question);
                setSubmitting(false);
            } else {
                // Fallback: refresh from server
                await mutate();
                setSubmitting(false);
            }

        } catch (err: any) {
            console.error(err);
            setSubmitting(false);
            setFeedback(null);
            alert(err.detail || "Failed to submit answer. Please try again.");
        }
    };

    const handleContinue = () => {
        if (pendingNextQuestion) {
            setCurrentQuestion(pendingNextQuestion);
            setQuestionNumber(prev => prev + 1);
            setAnswer("");
            setFeedback(null);
            setPendingNextQuestion(null);
        }
    };

    const handleViewResults = () => {
        if (examState) {
            router.push(`/student/results/${examState.attempt.id}`);
        } else {
            router.push("/student");
        }
    };

    const handleEndExam = async () => {
        if (!confirm("Are you sure you want to end the exam early?")) return;
        try {
            await endExam();
            if (examState) {
                router.push(`/student/results/${examState.attempt.id}`);
            } else {
                router.push("/student");
            }
        } catch (err) {
            console.error(err);
        }
    };

    // Loading state
    if (isLoading && !currentQuestion) {
        return (
            <div className="h-screen flex flex-col items-center justify-center gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
                <span className="text-zinc-500">Loading exam...</span>
            </div>
        );
    }

    // No active exam
    if (!examState && !currentQuestion) {
        return (
            <div className="h-screen flex flex-col items-center justify-center p-6 text-center">
                <h2 className="text-xl font-semibold mb-2">No Active Exam</h2>
                <button onClick={() => router.push("/student")} className="text-blue-600 underline">
                    Return to Dashboard
                </button>
            </div>
        );
    }

    // No question available (shouldn't happen normally with our new logic)
    if (!currentQuestion && !feedback) {
        return (
            <div className="h-screen flex flex-col items-center justify-center p-6 text-center gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
                <span className="text-zinc-500">Generating question...</span>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white flex flex-col">
            {/* Top Bar */}
            <header className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between bg-white z-20 shadow-sm sticky top-0">
                <div className="flex items-center gap-4">
                    <span className="font-serif font-bold text-xl text-zinc-900">
                        Question {questionNumber}
                    </span>
                    <div className="h-6 w-px bg-zinc-200"></div>
                    {examState?.rating_so_far && (
                        <span className="text-xs font-semibold px-2 py-1 bg-zinc-100 rounded text-zinc-600 uppercase tracking-wide">
                            Rating: {examState.rating_so_far.replace('_', ' ')}
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-6">
                    <div className={`flex items-center gap-2 font-mono text-lg font-medium ${timeLeft < 60 ? 'text-red-500 animate-pulse' : 'text-zinc-700'}`}>
                        <Clock size={20} />
                        {formatTime(timeLeft)}
                    </div>
                    <button
                        onClick={handleEndExam}
                        disabled={submitting}
                        className="text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50"
                    >
                        End Exam
                    </button>
                </div>
            </header>

            <main className="flex-1 max-w-4xl mx-auto w-full p-6 md:p-12 flex flex-col">
                {/* Question Area */}
                <div className="flex-1 flex flex-col justify-center min-h-[400px]">
                    {currentQuestion && (
                        <div className="prose prose-lg max-w-none mb-8 text-zinc-800">
                            <p className="whitespace-pre-wrap">{currentQuestion.question_text}</p>
                        </div>
                    )}

                    {/* Feedback Panel */}
                    {feedback && (
                        <div className={`mb-6 p-5 rounded-xl border-2 flex items-start gap-4
                            ${feedback.correct
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                                : 'bg-amber-50 border-amber-200 text-amber-800'}
                        `}>
                            {feedback.correct
                                ? <CheckCircle className="shrink-0 mt-0.5 w-6 h-6" />
                                : <AlertTriangle className="shrink-0 mt-0.5 w-6 h-6" />
                            }
                            <div className="flex-1">
                                <h4 className="font-bold text-base mb-1">
                                    {feedback.correct ? "Correct!" : "Needs Improvement"}
                                </h4>
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">{feedback.text}</p>
                            </div>
                        </div>
                    )}

                    {/* Continue / Results Button */}
                    {feedback && (
                        <div className="mb-6 flex justify-center">
                            {examEnded ? (
                                <button
                                    onClick={handleViewResults}
                                    className="px-8 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-semibold shadow-lg flex items-center gap-3 transition-all transform hover:-translate-y-1"
                                >
                                    <CheckCircle size={20} />
                                    View Your Results
                                </button>
                            ) : pendingNextQuestion ? (
                                <button
                                    onClick={handleContinue}
                                    className="px-8 py-4 bg-zinc-900 hover:bg-black text-white rounded-xl font-semibold shadow-lg flex items-center gap-3 transition-all transform hover:-translate-y-1"
                                >
                                    Continue to Next Question
                                    <ArrowRight size={20} />
                                </button>
                            ) : null}
                        </div>
                    )}

                    {/* Answer Input - Only show when not showing feedback */}
                    {!feedback && (
                        <div className="relative">
                            <textarea
                                value={answer}
                                onChange={(e) => setAnswer(e.target.value)}
                                disabled={submitting}
                                placeholder="Type your answer here..."
                                className="w-full h-40 p-5 rounded-xl border border-zinc-200 bg-zinc-50 focus:bg-white focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none resize-none text-zinc-800 placeholder:text-zinc-400 font-medium disabled:opacity-60"
                            />

                            <div className="mt-6 flex justify-end">
                                <button
                                    onClick={handleSubmit}
                                    disabled={!answer.trim() || submitting}
                                    className={`px-8 py-3 rounded-xl font-semibold shadow-lg transition-all flex items-center gap-2 transform active:scale-95
                                        ${(!answer.trim() || submitting)
                                            ? 'bg-zinc-100 text-zinc-400 shadow-none cursor-not-allowed'
                                            : 'bg-zinc-900 hover:bg-black text-white shadow-zinc-200 hover:-translate-y-1'
                                        }
                                    `}
                                >
                                    {submitting ? (
                                        <>
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                            <span>Evaluating...</span>
                                        </>
                                    ) : (
                                        <>
                                            <span>Submit Answer</span>
                                            <Send size={18} />
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
