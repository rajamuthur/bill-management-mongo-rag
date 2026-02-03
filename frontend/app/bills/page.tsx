'use client';
import React, { useEffect, useState } from 'react';

interface BillItem {
    description: string;
    amount: number | null;
    quantity: number;
    rate: number | null;
    tax: number | null;
}

interface Bill {
    _id: string;
    vendor: string;
    bill_date: string | null;
    total_amount: number;
    category: string | null;
    payment_method: string | null;
    bill_no: string | null;
    source_file: string | null;
    file_path: string | null;
    items: BillItem[];
}

export default function BillsPage() {
    const [bills, setBills] = useState<Bill[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedBill, setExpandedBill] = useState<string | null>(null);
    const [mounted, setMounted] = useState(false);

    // Search & Filter State
    const [search, setSearch] = useState("");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [sortBy, setSortBy] = useState("bill_date");
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
    const [totalPages, setTotalPages] = useState(1);
    const [totalBills, setTotalBills] = useState(0);

    // Debounce Search
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1); // Reset to page 1 on search
            fetchBills();
        }, 500);
        return () => clearTimeout(timer);
    }, [search]);

    // Fetch on State Change
    useEffect(() => {
        fetchBills();
    }, [page, pageSize, sortBy, sortOrder]);

    useEffect(() => {
        setMounted(true);
    }, []);

    const fetchBills = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: pageSize.toString(),
                sort_by: sortBy,
                sort_order: sortOrder,
                search: search
            });
            const res = await fetch(`/api/bills?${params.toString()}`);
            const data = await res.json();

            if (data.data) {
                setBills(data.data);
                setTotalPages(data.pagination.total_pages);
                setTotalBills(data.pagination.total);
            }
        } catch (error) {
            console.error("Failed to fetch bills", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSort = (field: string) => {
        if (sortBy === field) {
            setSortOrder(sortOrder === "asc" ? "desc" : "asc");
        } else {
            setSortBy(field);
            setSortOrder("desc"); // Default new sort to desc
        }
    };

    const handleDownload = (filePath: string) => {
        const encodedPath = encodeURIComponent(filePath);
        window.open(`/api/download?path=${encodedPath}`, '_blank');
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Expense History</h1>
                    <p className="text-slate-500 mt-1">Manage and track your recent bill payments.</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Search vendor, category..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none w-64"
                        />
                        <svg className="w-4 h-4 text-slate-400 absolute left-3 top-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                    </div>
                </div>
            </div>

            <div className="bg-white shadow-xl shadow-indigo-100/50 rounded-2xl overflow-hidden border border-slate-100">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-100">
                        <thead>
                            <tr className="bg-slate-50/50">
                                <th onClick={() => handleSort("vendor")} className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100">
                                    Vendor {sortBy === "vendor" && (sortOrder === "asc" ? "↑" : "↓")}
                                </th>
                                <th onClick={() => handleSort("bill_date")} className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100">
                                    Date {sortBy === "bill_date" && (sortOrder === "asc" ? "↑" : "↓")}
                                </th>
                                <th onClick={() => handleSort("category")} className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100">
                                    Category {sortBy === "category" && (sortOrder === "asc" ? "↑" : "↓")}
                                </th>
                                <th onClick={() => handleSort("total_amount")} className="px-6 py-4 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:bg-slate-100">
                                    Amount {sortBy === "total_amount" && (sortOrder === "asc" ? "↑" : "↓")}
                                </th>
                                <th className="px-6 py-4 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Source</th>
                                <th className="px-6 py-4 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                                    </td>
                                </tr>
                            ) : bills.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                                        No bills found matching your search.
                                    </td>
                                </tr>
                            ) : (
                                bills.map((bill) => {
                                    const billIdForExpansion = bill._id || `fallback-${bill.bill_no || Math.random()}`;
                                    return (
                                        <React.Fragment key={bill._id}>
                                            <tr
                                                onClick={() => {
                                                    setExpandedBill(expandedBill === billIdForExpansion ? null : billIdForExpansion);
                                                }}
                                                className={`group hover:bg-indigo-50/30 transition-colors duration-200 cursor-pointer ${expandedBill === billIdForExpansion ? 'bg-indigo-50/40' : ''}`}
                                            >
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center">
                                                        <div className="h-10 w-10 flex-shrink-0 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center text-indigo-600 font-bold text-lg shadow-sm">
                                                            {(bill.vendor || '?').charAt(0).toUpperCase()}
                                                        </div>
                                                        <div className="ml-4">
                                                            <div className="text-sm font-bold text-slate-900 group-hover:text-indigo-700 transition-colors">{bill.vendor || 'Unknown Vendor'}</div>
                                                            <div className="text-xs text-slate-500">#{bill.bill_no || 'NA'}</div>
                                                        </div>
                                                    </div>
                                                </td>

                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600" suppressHydrationWarning>
                                                    {mounted && bill.bill_date ? (
                                                        <div className="flex items-center gap-2">
                                                            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                                                            {new Date(bill.bill_date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                                                        </div>
                                                    ) : (
                                                        <span className="text-slate-400 italic">--/--/----</span>
                                                    )}
                                                </td>

                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${bill.category ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>
                                                        {bill.category || 'Uncategorized'}
                                                    </span>
                                                </td>

                                                <td className="px-6 py-4 whitespace-nowrap text-right">
                                                    <div className="text-sm font-bold text-slate-900">
                                                        ₹{bill.total_amount?.toLocaleString('en-IN') || '0.00'}
                                                    </div>
                                                </td>

                                                <td className="px-6 py-4 whitespace-nowrap text-center">
                                                    {bill.source_file ? (
                                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-700/10">
                                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                                            OCR
                                                        </span>
                                                    ) : (
                                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20">
                                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                                                            Manual
                                                        </span>
                                                    )}
                                                </td>

                                                <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                                                    <div className="flex items-center justify-center gap-3">
                                                        {bill.file_path && (
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleDownload(bill.file_path!);
                                                                }}
                                                                className="text-slate-400 hover:text-indigo-600 transition-colors p-1.5 hover:bg-indigo-50 rounded-full"
                                                                title="Download Original Bill"
                                                            >
                                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                                </svg>
                                                            </button>
                                                        )}
                                                        <button className={`text-slate-400 transition-transform duration-200 ${expandedBill === billIdForExpansion ? 'rotate-180 text-indigo-600' : ''}`}>
                                                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>

                                            {expandedBill === billIdForExpansion && (
                                                <tr className="bg-indigo-50/40">
                                                    <td colSpan={6} className="px-6 py-4">
                                                        <div className="rounded-xl bg-white border border-indigo-100 p-4 shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
                                                            <div className="flex items-center justify-between mb-4 pb-2 border-b border-indigo-50">
                                                                <h4 className="text-sm font-bold text-indigo-900 uppercase tracking-widest flex items-center gap-2">
                                                                    <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                                                                    Bill Items
                                                                </h4>
                                                                <div className="text-xs text-indigo-400 font-mono">ID: {bill._id}</div>
                                                            </div>

                                                            {bill.items.length > 0 ? (
                                                                <div className="space-y-2">
                                                                    {bill.items.map((item, idx) => (
                                                                        <div key={`${bill._id}-item-${idx}`} className="flex justify-between items-center text-sm p-2 hover:bg-slate-50 rounded-lg transition-colors">
                                                                            <div className="flex items-start gap-3">
                                                                                <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500 mt-0.5">
                                                                                    {idx + 1}
                                                                                </div>
                                                                                <div>
                                                                                    <div className="font-medium text-slate-800">{item.description}</div>
                                                                                    <div className="text-xs text-slate-500">Qty: {item.quantity} {item.rate ? `× ₹${item.rate}` : ''}</div>
                                                                                </div>
                                                                            </div>
                                                                            <div className="font-mono font-bold text-slate-700">
                                                                                ₹{item.amount?.toLocaleString('en-IN') || '0.00'}
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            ) : (
                                                                <div className="text-center py-6 text-slate-400 text-sm italic">
                                                                    No itemized details available for this bill.
                                                                </div>
                                                            )}

                                                            <div className="mt-4 pt-3 border-t border-indigo-50 grid grid-cols-2 gap-4 text-xs text-slate-500">
                                                                <div>
                                                                    <span className="font-semibold text-slate-700">Payment Method:</span> {bill.payment_method || 'Unknown'}
                                                                </div>
                                                                <div className="text-right">
                                                                    <span className="font-semibold text-slate-700">Tax/Fees:</span> ₹{bill.items.reduce((acc, curr) => acc + (curr.tax || 0), 0).toFixed(2)}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                }))}
                        </tbody>
                    </table>

                    {/* Pagination Controls */}
                    <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
                        <div className="text-sm text-slate-500">
                            Showing page <span className="font-bold text-slate-900">{page}</span> of <span className="font-bold text-slate-900">{totalPages}</span> ({totalBills} total)
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPage(Math.max(1, page - 1))}
                                disabled={page === 1}
                                className="px-3 py-1 bg-white border border-slate-300 rounded text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Previous
                            </button>
                            <button
                                onClick={() => setPage(Math.min(totalPages, page + 1))}
                                disabled={page === totalPages}
                                className="px-3 py-1 bg-white border border-slate-300 rounded text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
