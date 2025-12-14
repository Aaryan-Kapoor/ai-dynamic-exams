export default function DashboardHeader() {
    return (
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-zinc-200 flex items-center justify-between px-8 sticky top-0 z-10 w-full">
            <div>
                <h2 className="font-serif text-xl font-bold text-zinc-800">
                    Midterm Examination Setup
                </h2>
                <div className="flex items-center text-xs text-zinc-500 mt-1">
                    <span>CS-101: Intro to Algorithms</span>
                    <span className="mx-2">•</span>
                    <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full font-medium">
                        AI Active
                    </span>
                </div>
            </div>

            <div className="flex gap-3">
                <button className="px-4 py-2 bg-white border border-zinc-200 text-zinc-600 rounded-lg text-sm font-medium hover:bg-zinc-50 shadow-sm transition cursor-pointer">
                    Discard
                </button>
                <button className="px-5 py-2 bg-zinc-900 text-white rounded-lg text-sm font-medium hover:bg-black shadow-lg shadow-zinc-300 transition flex items-center gap-2 cursor-pointer">
                    <span>Deploy Exam</span>
                    <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M14 5l7 7m0 0l-7 7m7-7H3"
                        ></path>
                    </svg>
                </button>
            </div>
        </header>
    );
}
