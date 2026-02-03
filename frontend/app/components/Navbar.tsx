"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Navbar() {
    const pathname = usePathname();

    const isActive = (path: string) => {
        return pathname === path ? "bg-indigo-50 text-indigo-600" : "text-slate-600 hover:text-indigo-600 hover:bg-slate-50";
    };

    return (
        <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-indigo-100 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16 items-center">
                    <div className="flex-shrink-0 flex items-center gap-2">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-xl">B</div>
                            <span className="font-bold text-xl tracking-tight text-indigo-900">BillManager</span>
                        </Link>
                    </div>
                    <div className="hidden sm:flex sm:space-x-8">
                        <Link href="/chat" className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/chat')}`}>Chat</Link>
                        <Link href="/upload" className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/upload')}`}>Upload</Link>
                        <Link href="/bills" className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/bills')}`}>Bills</Link>
                    </div>
                </div>
            </div>
        </nav>
    );
}
