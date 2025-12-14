"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import DashboardHeader from "@/components/DashboardHeader";
import KnowledgeBaseCard from "@/components/KnowledgeBaseCard";
import ExamConfigPanel from "@/components/ExamConfigPanel";
import { useTeacherDashboard, saveExamConfig } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
    // We start with undefined to let backend defaults take over or wait for load
    const [deptId, setDeptId] = useState<number | undefined>(undefined);
    const [grade, setGrade] = useState<number | undefined>(undefined);

    // Fetch data
    const { dashboard, isLoading, isError, mutate } = useTeacherDashboard(deptId, grade);

    // Update local state when dashboard loads first time to match server defaults
    if (dashboard && deptId === undefined) {
        setDeptId(dashboard.current_department_id);
    }
    if (dashboard && grade === undefined) {
        setGrade(dashboard.current_grade_level);
    }

    const handleSaveConfig = async (configData: any) => {
        if (!dashboard) return;
        try {
            await saveExamConfig({
                ...configData,
                department_id: deptId || dashboard.current_department_id,
                grade_level: grade || dashboard.current_grade_level
            });
            await mutate(); // Refresh
            alert("Configuration saved successfully.");
        } catch (err) {
            console.error(err);
            alert("Failed to save configuration.");
        }
    };

    if (isLoading && !dashboard) {
        return (
            <div className="flex w-full h-screen items-center justify-center bg-[#F3F4F6]">
                <Loader2 className="animate-spin text-zinc-400" size={32} />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex w-full h-screen items-center justify-center bg-[#F3F4F6] text-red-500">
                Error loading dashboard. Please check your permissions or connection.
            </div>
        );
    }

    return (
        <div className="flex w-full h-screen bg-[#F3F4F6] overflow-hidden text-zinc-800">
            <Sidebar />

            <main className="flex-1 flex flex-col h-full overflow-hidden relative">
                <DashboardHeader />

                {/* Scrollable Workspace */}
                <div className="flex-1 overflow-y-auto p-8">
                    <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
                        {/* COLUMN 1: AI & Content (Lectures) */}
                        <div className="lg:col-span-4 space-y-6">
                            {/* AI Context Card */}
                            <KnowledgeBaseCard
                                departmentId={deptId || 0}
                                gradeLevel={grade || 1}
                                lectures={dashboard?.lectures || []}
                                onUploadSuccess={() => mutate()}
                            />

                            {/* Class Context */}
                            <div className="bg-white p-6 rounded-2xl shadow-soft border border-zinc-100">
                                <h3 className="font-serif font-semibold text-zinc-900 mb-4">
                                    Target Audience
                                </h3>
                                <div className="space-y-4">
                                    <div>
                                        <label className="text-xs font-semibold text-zinc-500 uppercase">
                                            Department
                                        </label>
                                        <select
                                            value={deptId}
                                            onChange={(e) => setDeptId(Number(e.target.value))}
                                            className="mt-1 w-full bg-zinc-50 border-none rounded-lg px-3 py-2.5 text-sm text-zinc-800 focus:ring-1 focus:ring-primary-500 cursor-pointer outline-none"
                                        >
                                            {dashboard?.departments.map(dept => (
                                                <option key={dept.id} value={dept.id}>
                                                    {dept.name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs font-semibold text-zinc-500 uppercase">
                                            Grade Level
                                        </label>
                                        <select
                                            value={grade}
                                            onChange={(e) => setGrade(Number(e.target.value))}
                                            className="mt-1 w-full bg-zinc-50 border-none rounded-lg px-3 py-2.5 text-sm text-zinc-800 focus:ring-1 focus:ring-primary-500 cursor-pointer outline-none"
                                        >
                                            <option value={1}>Year 1 (Freshman)</option>
                                            <option value={2}>Year 2 (Sophomore)</option>
                                            <option value={3}>Year 3 (Junior)</option>
                                            <option value={4}>Year 4 (Senior)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* COLUMN 2: Exam Configuration */}
                        <div className="lg:col-span-8 space-y-6">
                            {/* Top Stats/Preview */}
                            <div className="grid grid-cols-3 gap-4">
                                <div className="bg-white p-4 rounded-xl border border-zinc-100 shadow-sm">
                                    <p className="text-xs text-zinc-500 uppercase font-semibold">
                                        Max Duration
                                    </p>
                                    <p className="text-2xl font-serif font-medium text-zinc-900 mt-1">
                                        {dashboard?.config?.max_duration_minutes || 0}m
                                    </p>
                                </div>
                                <div className="bg-white p-4 rounded-xl border border-zinc-100 shadow-sm">
                                    <p className="text-xs text-zinc-500 uppercase font-semibold">
                                        Reliability Score
                                    </p>
                                    <p className="text-2xl font-serif font-medium text-emerald-600 mt-1">
                                        Active
                                    </p>
                                </div>
                                <div className="bg-white p-4 rounded-xl border border-zinc-100 shadow-sm">
                                    <p className="text-xs text-zinc-500 uppercase font-semibold">
                                        Max Questions
                                    </p>
                                    <p className="text-2xl font-serif font-medium text-zinc-900 mt-1">
                                        {dashboard?.config?.max_questions || 0}
                                    </p>
                                </div>
                            </div>

                            {/* Main Config Panel */}
                            <ExamConfigPanel
                                config={dashboard?.config}
                                onSave={handleSaveConfig}
                            />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
