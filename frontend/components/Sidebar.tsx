"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
    Settings,
    Library,
    BarChart2,
    LogOut,
    UserCircle
} from "lucide-react";
import { logout, useUser } from "@/lib/api";
import clsx from "clsx";

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user } = useUser();

    const handleLogout = async () => {
        await logout();
        router.push("/login");
    };

    const navItems = [
        { name: 'Exam Config', href: '/dashboard', icon: Settings },
        { name: 'Lectures', href: '/dashboard/lectures', icon: Library },
        { name: 'Results', href: '/dashboard/results', icon: BarChart2 },
    ];

    return (
        <aside className="w-20 lg:w-64 bg-white border-r border-zinc-200 flex flex-col justify-between z-20 h-screen fixed lg:relative sticky top-0">
            <div>
                {/* Header */}
                <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-zinc-100">
                    <div className="w-8 h-8 bg-zinc-900 rounded-lg flex items-center justify-center text-white shrink-0">
                        <span className="font-serif font-bold italic">A</span>
                    </div>
                    <span className="ml-3 font-serif font-bold text-lg text-zinc-900 hidden lg:block tracking-tight">
                        Aequitas
                    </span>
                </div>

                {/* Nav */}
                <nav className="mt-6 px-3 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={clsx(
                                    "flex items-center px-3 py-2.5 rounded-lg transition group",
                                    isActive
                                        ? "bg-zinc-100 text-zinc-900 font-medium"
                                        : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
                                )}
                            >
                                <item.icon
                                    size={20}
                                    className={clsx(
                                        "shrink-0",
                                        isActive ? "text-zinc-900" : "text-zinc-400 group-hover:text-zinc-600"
                                    )}
                                />
                                <span className="ml-3 text-sm hidden lg:block">
                                    {item.name}
                                </span>
                            </Link>
                        );
                    })}
                </nav>
            </div>

            {/* Profile */}
            <div className="p-4 border-t border-zinc-100">
                <div className="flex items-center gap-3 w-full p-2 rounded-lg mb-2">
                    <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400">
                        <UserCircle size={24} />
                    </div>
                    <div className="hidden lg:block text-left overflow-hidden">
                        <p className="text-sm font-semibold text-zinc-900 truncate">
                            {user?.full_name || "Instructor"}
                        </p>
                        <p className="text-xs text-zinc-500 truncate">{user?.role}</p>
                    </div>
                </div>
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 w-full p-2 rounded-lg text-red-600 hover:bg-red-50 transition text-sm"
                >
                    <LogOut size={20} className="shrink-0" />
                    <span className="hidden lg:block">Sign Out</span>
                </button>
            </div>
        </aside>
    );
}
