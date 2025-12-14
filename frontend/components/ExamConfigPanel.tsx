"use client";

import { ExamConfig } from "@/lib/api-types";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";

interface ExamConfigPanelProps {
    config?: ExamConfig;
    onSave?: (config: any) => void;
}

export default function ExamConfigPanel({ config, onSave }: ExamConfigPanelProps) {
    const [formData, setFormData] = useState<Partial<ExamConfig>>({
        max_duration_minutes: 30,
        difficulty_min: 2,
        difficulty_max: 4,
        max_attempts: 3,
        stop_consecutive_incorrect: 3,
        stop_slow_seconds: 300,
        max_questions: 10,
    });

    useEffect(() => {
        if (config) {
            setFormData({
                max_duration_minutes: config.max_duration_minutes,
                difficulty_min: config.difficulty_min,
                difficulty_max: config.difficulty_max,
                max_attempts: config.max_attempts,
                stop_consecutive_incorrect: config.stop_consecutive_incorrect,
                stop_slow_seconds: config.stop_slow_seconds,
                max_questions: config.max_questions,
            });
        }
    }, [config]);

    const handleChange = (field: keyof ExamConfig, value: string) => {
        setFormData(prev => ({
            ...prev,
            [field]: parseInt(value) || 0
        }));
    };

    const handleSave = () => {
        if (onSave) onSave(formData);
    };

    return (
        <div className="bg-white rounded-2xl shadow-soft border border-zinc-100 overflow-hidden">
            <div className="px-8 py-6 border-b border-zinc-100 flex justify-between items-center">
                <div>
                    <h3 className="font-serif text-lg font-semibold text-zinc-900">
                        Exam Parameters
                    </h3>
                    <p className="text-sm text-zinc-500 mt-1">
                        Configure how the AI adapts to student performance.
                    </p>
                </div>
                <button
                    onClick={handleSave}
                    className="flex items-center gap-2 bg-zinc-900 hover:bg-black text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                    <Save size={16} />
                    Save Configuration
                </button>
            </div>

            <div className="p-8 space-y-10">
                {/* Difficulty Range */}
                <div>
                    <div className="flex justify-between items-end mb-4">
                        <div>
                            <label className="text-sm font-semibold text-zinc-900">
                                Adaptive Difficulty Range (1-5)
                            </label>
                            <p className="text-xs text-zinc-500 mt-1">
                                Questions will fluctuate within this complexity band.
                            </p>
                        </div>
                        <span className="text-xs font-mono bg-zinc-100 px-2 py-1 rounded text-zinc-600">
                            Level {formData.difficulty_min} — {formData.difficulty_max}
                        </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Min Difficulty</label>
                            <input
                                type="number"
                                min="1" max="5"
                                value={formData.difficulty_min}
                                onChange={(e) => handleChange('difficulty_min', e.target.value)}
                                className="soft-input w-full p-2.5 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Max Difficulty</label>
                            <input
                                type="number"
                                min="1" max="5"
                                value={formData.difficulty_max}
                                onChange={(e) => handleChange('difficulty_max', e.target.value)}
                                className="soft-input w-full p-2.5 rounded-lg text-sm"
                            />
                        </div>
                    </div>
                </div>

                <hr className="border-zinc-50" />

                {/* Grid Inputs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4">
                        <label className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                            <svg
                                className="w-4 h-4 text-zinc-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                                ></path>
                            </svg>
                            Time & Questions
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <span className="text-xs text-zinc-500 mb-1 block">
                                    Total Duration (m)
                                </span>
                                <input
                                    type="number"
                                    value={formData.max_duration_minutes}
                                    onChange={(e) => handleChange('max_duration_minutes', e.target.value)}
                                    className="soft-input w-full p-2.5 rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <span className="text-xs text-zinc-500 mb-1 block">
                                    Max Questions
                                </span>
                                <input
                                    type="number"
                                    value={formData.max_questions}
                                    onChange={(e) => handleChange('max_questions', e.target.value)}
                                    className="soft-input w-full p-2.5 rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <label className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                            <svg
                                className="w-4 h-4 text-zinc-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                ></path>
                            </svg>
                            Stop Conditions
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <span className="text-xs text-zinc-500 mb-1 block">
                                    Max Retakes
                                </span>
                                <input
                                    type="number"
                                    value={formData.max_attempts}
                                    onChange={(e) => handleChange('max_attempts', e.target.value)}
                                    className="soft-input w-full p-2.5 rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <span className="text-xs text-zinc-500 mb-1 block">
                                    Consecutive Fails
                                </span>
                                <input
                                    type="number"
                                    value={formData.stop_consecutive_incorrect}
                                    onChange={(e) => handleChange('stop_consecutive_incorrect', e.target.value)}
                                    className="soft-input w-full p-2.5 rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <span className="text-xs text-zinc-500 mb-1 block">
                                    Slow Cutoff (s)
                                </span>
                                <input
                                    type="number"
                                    value={formData.stop_slow_seconds}
                                    onChange={(e) => handleChange('stop_slow_seconds', e.target.value)}
                                    className="soft-input w-full p-2.5 rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
