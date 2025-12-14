"use client";

import { fetcher } from "@/lib/api";
import { ExamAttempt } from "@/lib/api-types";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { CheckCircle2, XCircle, ArrowLeft, Award } from "lucide-react";
import { useParams } from "next/navigation";

export default function ExamResultsPage() {
    const params = useParams();
    const id = params.id;
    const router = useRouter();

    const { data: attempt, error, isLoading } = useSWR<ExamAttempt>(id ? `/student/results/${id}` : null, fetcher);

    if (isLoading) return <div className="h-screen flex items-center justify-center">Loading results...</div>;
    if (error || !attempt) return <div className="h-screen flex items-center justify-center text-red-500">Results not found.</div>;

    const percentage = attempt.score !== undefined ? attempt.score : 0;
    const rating = attempt.rating ? attempt.rating.replace('_', ' ') : 'Pending';
    const isPass = percentage >= 60; // Assuming 60 is pass for visual

    return (
        <div className="min-h-screen bg-zinc-50 py-12 px-6 flex items-center justify-center">
            <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl border border-zinc-100 overflow-hidden">
                {/* Decoration Header */}
                <div className={`h-32 w-full flex items-center justify-center relative overflow-hidden
            ${isPass ? 'bg-emerald-600' : 'bg-rose-600'}
         `}>
                    <div className="absolute inset-0 opacity-20"
                        style={{
                            backgroundImage: "radial-gradient(white 1px, transparent 1px)",
                            backgroundSize: "24px 24px"
                        }}
                    ></div>
                    <div className="relative z-10 text-white flex flex-col items-center">
                        {isPass ? <Award size={48} className="mb-2" /> : <XCircle size={48} className="mb-2" />}
                        <h1 className="text-3xl font-serif font-bold tracking-tight">
                            {isPass ? "Assessment Completed" : "Assessment Ended"}
                        </h1>
                    </div>
                </div>

                <div className="p-8 text-center">
                    <div className="mb-8">
                        <span className="block text-sm font-semibold text-zinc-400 uppercase tracking-widest mb-2">Final Score</span>
                        <div className="flex items-end justify-center gap-2 leading-none">
                            <span className="text-6xl font-bold text-zinc-900">{percentage.toFixed(1)}</span>
                            <span className="text-2xl font-medium text-zinc-400 mb-1.5">%</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-8">
                        <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                            <div className="text-xs text-zinc-500 uppercase font-semibold mb-1">Qualitative Rating</div>
                            <div className="text-lg font-medium text-zinc-900 capitalize">{rating}</div>
                        </div>
                        <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                            <div className="text-xs text-zinc-500 uppercase font-semibold mb-1">Questions Answered</div>
                            <div className="text-lg font-medium text-zinc-900">{attempt.questions_answered}</div>
                        </div>
                        <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-100 col-span-2">
                            <div className="text-xs text-zinc-500 uppercase font-semibold mb-1">Completion Status</div>
                            <div className="text-lg font-medium text-zinc-900 capitalize">
                                {attempt.ended_reason?.replace('_', ' ') || 'Unknown'}
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <button
                            onClick={() => router.push("/student")}
                            className="flex items-center gap-2 px-6 py-3 rounded-full bg-zinc-900 text-white font-medium hover:bg-zinc-800 transition-colors"
                        >
                            <ArrowLeft size={18} />
                            Return to Dashboard
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
