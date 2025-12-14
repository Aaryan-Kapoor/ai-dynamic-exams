"use client";

import { fetcher } from "@/lib/api";
import { User, Role } from "@/lib/api-types";
import useSWR from "swr";
import { useState } from "react";
import { Plus, Search, User as UserIcon, Shield, GraduationCap, School } from "lucide-react";
import { useRouter } from "next/navigation";

export default function AdminPage() {
    const router = useRouter();
    const { data: users, error, mutate } = useSWR<User[]>('/admin/users', fetcher);
    const [filterRole, setFilterRole] = useState<Role | "all">("all");
    const [showAddModal, setShowAddModal] = useState(false);

    // Form State
    const [newUser, setNewUser] = useState({
        university_id: "",
        password: "",
        full_name: "",
        role: Role.student,
        grade_level: 1
    });

    const filteredUsers = users?.filter(u => filterRole === "all" || u.role === filterRole) || [];

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch("/admin/users", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newUser)
            });
            if (!res.ok) throw await res.json();
            setShowAddModal(false);
            setNewUser({ university_id: "", password: "", full_name: "", role: Role.student, grade_level: 1 });
            mutate();
            alert("User created successfully");
        } catch (err: any) {
            alert(err.detail || "Failed to create user");
        }
    };

    return (
        <div className="min-h-screen bg-zinc-50 font-sans text-zinc-800">
            <header className="bg-zinc-900 text-white px-8 py-4 flex items-center justify-between shadow-md">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/10 rounded-lg">
                        <Shield size={20} />
                    </div>
                    <h1 className="text-lg font-bold tracking-wide">System Administration</h1>
                </div>
                <button onClick={() => router.push("/login")} className="text-sm text-zinc-400 hover:text-white">
                    Logout
                </button>
            </header>

            <main className="max-w-7xl mx-auto p-8">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-zinc-900">User Management</h2>
                        <p className="text-zinc-500">Manage access and roles for the university portal.</p>
                    </div>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="bg-primary-600 hover:bg-primary-700 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 shadow-lg shadow-primary-200 transition-transform active:scale-95"
                    >
                        <Plus size={18} />
                        Add User
                    </button>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
                    {["all", Role.student, Role.teacher, Role.system_admin].map((r) => (
                        <button
                            key={r}
                            onClick={() => setFilterRole(r as Role | "all")}
                            className={`px-4 py-2 rounded-full text-sm font-medium capitalize transition-colors
                        ${filterRole === r
                                    ? "bg-zinc-900 text-white"
                                    : "bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50"
                                }
                    `}
                        >
                            {r.toString().replace('_', ' ')}
                        </button>
                    ))}
                </div>

                {/* User Table */}
                <div className="bg-white rounded-xl shadow-sm border border-zinc-200 overflow-hidden">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 uppercase tracking-wider text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4">Full Name</th>
                                <th className="px-6 py-4">University ID</th>
                                <th className="px-6 py-4">Role</th>
                                <th className="px-6 py-4">Level</th>
                                <th className="px-6 py-4">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                            {(!users && !error) && (
                                <tr><td colSpan={5} className="px-6 py-8 text-center text-zinc-400">Loading users...</td></tr>
                            )}
                            {filteredUsers.map((u) => (
                                <tr key={u.id} className="hover:bg-zinc-50 transition-colors">
                                    <td className="px-6 py-4 font-medium text-zinc-900 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500">
                                            {u.role === Role.student ? <GraduationCap size={16} /> :
                                                u.role === Role.teacher ? <School size={16} /> : <Shield size={16} />}
                                        </div>
                                        {u.full_name}
                                    </td>
                                    <td className="px-6 py-4 font-mono text-zinc-500">{u.university_id}</td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                                    ${u.role === Role.student ? 'bg-blue-50 text-blue-700' :
                                                u.role === Role.teacher ? 'bg-purple-50 text-purple-700' :
                                                    'bg-zinc-100 text-zinc-800'}
                                 `}>
                                            {u.role.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-zinc-500">
                                        {u.grade_level ? `Year ${u.grade_level}` : '-'}
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex w-2 h-2 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                                    </td>
                                </tr>
                            ))}
                            {filteredUsers.length === 0 && users && (
                                <tr><td colSpan={5} className="px-6 py-8 text-center text-zinc-400">No users found.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </main>

            {/* Add User Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 animate-in zoom-in-95 duration-200">
                        <h3 className="text-xl font-bold text-zinc-900 mb-6">Create New User</h3>
                        <form onSubmit={handleCreateUser} className="space-y-4">
                            <div>
                                <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Full Name</label>
                                <input
                                    required
                                    type="text"
                                    className="soft-input w-full p-3 rounded-lg"
                                    value={newUser.full_name}
                                    onChange={e => setNewUser({ ...newUser, full_name: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">ID</label>
                                    <input
                                        required
                                        type="text"
                                        className="soft-input w-full p-3 rounded-lg"
                                        value={newUser.university_id}
                                        onChange={e => setNewUser({ ...newUser, university_id: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Password</label>
                                    <input
                                        required
                                        type="password"
                                        className="soft-input w-full p-3 rounded-lg"
                                        value={newUser.password}
                                        onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Role</label>
                                    <select
                                        className="soft-input w-full p-3 rounded-lg"
                                        value={newUser.role}
                                        onChange={e => setNewUser({ ...newUser, role: e.target.value as Role })}
                                    >
                                        <option value={Role.student}>Student</option>
                                        <option value={Role.teacher}>Teacher</option>
                                        <option value={Role.system_admin}>Admin</option>
                                    </select>
                                </div>
                                {newUser.role === Role.student && (
                                    <div>
                                        <label className="block text-xs font-semibold text-zinc-500 uppercase mb-1">Year</label>
                                        <select
                                            className="soft-input w-full p-3 rounded-lg"
                                            value={newUser.grade_level}
                                            onChange={e => setNewUser({ ...newUser, grade_level: Number(e.target.value) })}
                                        >
                                            <option value={1}>1 (Freshman)</option>
                                            <option value={2}>2 (Sophomore)</option>
                                            <option value={3}>3 (Junior)</option>
                                            <option value={4}>4 (Senior)</option>
                                        </select>
                                    </div>
                                )}
                            </div>

                            <div className="flex justify-end gap-3 mt-8">
                                <button
                                    type="button"
                                    onClick={() => setShowAddModal(false)}
                                    className="px-4 py-2 text-zinc-500 hover:bg-zinc-100 rounded-lg font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-6 py-2 bg-zinc-900 text-white rounded-lg font-medium hover:bg-black"
                                >
                                    Create User
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
