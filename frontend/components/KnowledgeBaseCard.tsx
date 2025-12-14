"use client";

import { LectureMaterial } from "@/lib/api-types";
import { useRef, useState } from "react";
import { UploadCloud, FileText, Trash2, Loader2 } from "lucide-react";
import { deleteLecture } from "@/lib/api";

interface KnowledgeBaseCardProps {
    departmentId: number;
    gradeLevel: number;
    lectures: LectureMaterial[];
    onUploadSuccess?: () => void;
}

export default function KnowledgeBaseCard({
    departmentId,
    gradeLevel,
    lectures,
    onUploadSuccess
}: KnowledgeBaseCardProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploading, setUploading] = useState(false);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        const formData = new FormData();
        formData.append("file", file);
        formData.append("department_id", departmentId.toString());
        formData.append("grade_level", gradeLevel.toString());

        try {
            const res = await fetch("/teacher/lectures/upload", {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Upload failed");
            if (onUploadSuccess) onUploadSuccess();
        } catch (err) {
            console.error(err);
            alert("Failed to upload lecture.");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this lecture? This action cannot be undone.")) return;
        try {
            await deleteLecture(id);
            if (onUploadSuccess) onUploadSuccess(); // Refresh list
        } catch (err) {
            console.error(err);
            alert("Failed to delete lecture.");
        }
    };

    return (
        <div className="bg-white p-6 rounded-2xl shadow-soft border border-zinc-100 h-full">
            <div className="flex items-center justify-between mb-4">
                <h3 className="font-serif font-semibold text-zinc-900">
                    Knowledge Base
                </h3>
                <span className="text-xs text-zinc-400 font-medium">
                    {lectures.length} documents
                </span>
            </div>

            <p className="text-xs text-zinc-500 mb-4 leading-relaxed">
                The AI generates questions based solely on the documents uploaded here.
            </p>

            {/* Dropzone */}
            <div
                onClick={() => !uploading && fileInputRef.current?.click()}
                className={`border-2 border-dashed border-zinc-200 hover:border-primary-500 hover:bg-primary-50/50 rounded-xl p-6 transition-all cursor-pointer group text-center
                   ${uploading ? 'opacity-50 cursor-wait' : ''}
                `}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".pdf"
                    onChange={handleUpload}
                    disabled={uploading}
                />

                <div className="w-10 h-10 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-white group-hover:shadow-sm transition">
                    {uploading ? (
                        <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
                    ) : (
                        <UploadCloud className="w-5 h-5 text-zinc-400 group-hover:text-primary-600" />
                    )}
                </div>
                <p className="text-sm font-medium text-zinc-700">
                    {uploading ? "Processing..." : "Upload Lecture PDF"}
                </p>
                <p className="text-[10px] text-zinc-400 mt-1">
                    OCR Enabled • Local Processing
                </p>
            </div>

            {/* File List */}
            <div className="mt-6 space-y-3 max-h-60 overflow-y-auto pr-1">
                {lectures.map((lecture) => (
                    <div key={lecture.id} className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg border border-zinc-100 hover:border-zinc-200 transition group/item">
                        <div className="w-8 h-8 bg-red-50 text-red-500 rounded flex items-center justify-center shrink-0">
                            <FileText size={16} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-zinc-900 truncate" title={lecture.original_filename}>
                                {lecture.original_filename}
                            </p>
                            <p className="text-[10px] text-zinc-500">
                                {new Date(lecture.created_at).toLocaleDateString()}
                            </p>
                        </div>
                        <button
                            onClick={() => handleDelete(lecture.id)}
                            className="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-red-50 rounded transition opacity-0 group-hover/item:opacity-100"
                            title="Delete Lecture"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                ))}

                {lectures.length === 0 && (
                    <div className="text-center py-4 text-zinc-400 text-xs italic">
                        No materials uploaded yet.
                    </div>
                )}
            </div>
        </div>
    );
}
