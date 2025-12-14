"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";
import { Role } from "@/lib/api-types";

export default function LoginPage() {
    const router = useRouter();
    const [uid, setUid] = useState("");
    const [pass, setPass] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const user = await login(uid, pass);
            if (user.role === Role.student) {
                router.push("/student");
            } else if (user.role === Role.system_admin) {
                router.push("/admin");
            } else {
                router.push("/dashboard"); // Teacher & others
            }
        } catch (err: any) {
            console.error("Login Error:", err);
            // If the error object has a detail field, use it
            setError(err.detail || "Authentication failed. Please check your credentials.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <section className="min-h-screen w-full flex items-center justify-center bg-[#F9FAFB] relative text-zinc-800">
            {/* Subtle Academic Background Pattern */}
            <div
                className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{
                    backgroundImage: "radial-gradient(#444 1px, transparent 1px)",
                    backgroundSize: "32px 32px",
                }}
            ></div>

            <div className="w-full max-w-md z-10 p-6">
                {/* Brand */}
                <div className="text-center mb-10">
                    <div className="w-12 h-12 mx-auto bg-primary-800 rounded-xl flex items-center justify-center shadow-lg text-white mb-4">
                        <svg
                            className="w-6 h-6"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                            ></path>
                        </svg>
                    </div>
                    <h1 className="font-serif text-3xl font-bold text-zinc-900 tracking-tight">
                        University Portal
                    </h1>
                    <p className="text-sm text-zinc-500 mt-2">
                        Secure Examination Environment
                    </p>
                </div>

                {/* Login Card */}
                <div className="bg-white rounded-2xl shadow-float p-8 border border-zinc-100">
                    <form className="space-y-6" onSubmit={handleLogin}>
                        {error && (
                            <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg">
                                {error}
                            </div>
                        )}
                        <div>
                            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                                University ID
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. s2001"
                                className="soft-input w-full rounded-lg px-4 py-3 text-zinc-900 placeholder:text-zinc-400 focus:outline-none"
                                value={uid}
                                onChange={(e) => setUid(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
                                Password
                            </label>
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="soft-input w-full rounded-lg px-4 py-3 text-zinc-900 placeholder:text-zinc-400 focus:outline-none"
                                value={pass}
                                onChange={(e) => setPass(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="flex items-center justify-between text-sm">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="rounded text-primary-600 focus:ring-primary-500 border-gray-300"
                                />
                                <span className="text-zinc-500">Remember device</span>
                            </label>
                            <a href="#" className="text-primary-800 hover:underline font-medium">
                                Need help?
                            </a>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className={`cursor-pointer w-full bg-zinc-900 hover:bg-black text-white font-medium py-3.5 rounded-lg shadow-lg shadow-zinc-200 transition-all transform hover:-translate-y-0.5 ${loading ? "opacity-70 cursor-not-allowed" : ""}`}
                        >
                            {loading ? "Authenticating..." : "Access System"}
                        </button>
                    </form>
                </div>

                <p className="text-center text-xs text-zinc-400 mt-8">
                    By signing in, you agree to the{" "}
                    <Link href="#" className="underline">
                        Academic Integrity Policy
                    </Link>
                    .
                </p>
            </div>
        </section>
    );
}
