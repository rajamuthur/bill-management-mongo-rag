"use client";

import { useState } from "react";

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function askQuestion(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: "u1",
          query
        })
      });

      const data = await res.json();
      setResponse(data.result);
    } catch (err) {
      setResponse({ error: "Failed to fetch response" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">Financial Assistant</h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Ask questions about your expenses, analyze trends, or find specific bill details using natural language.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-xl shadow-indigo-100/50 border border-slate-100 p-2">
        <form onSubmit={askQuestion} className="relative flex items-center">
          <div className="absolute left-4 text-slate-400">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="How much did I spend on groceries last month?"
            className="w-full pl-12 pr-32 py-4 rounded-xl text-lg text-slate-900 placeholder:text-slate-400 border-none ring-0 focus:ring-0 outline-none bg-transparent"
            disabled={loading}
          />
          <div className="absolute right-2">
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-all shadow-md shadow-indigo-200 flex items-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Ask</span>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {response && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center gap-2 px-1">
            <div className="h-px bg-slate-200 flex-1"></div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Analysis Result</span>
            <div className="h-px bg-slate-200 flex-1"></div>
          </div>

          <div className="bg-white rounded-2xl shadow-lg border border-slate-100 overflow-hidden">
            <div className="bg-indigo-50/50 px-6 py-3 border-b border-indigo-50 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></div>
              <span className="text-sm font-medium text-indigo-900">AI Response</span>
            </div>
            <div className="p-6">
              {/* Check if response is an array of objects for Table View */}
              {Array.isArray(response) && response.length > 0 && typeof response[0] === 'object' ? (
                <div className="overflow-x-auto mb-6 border border-slate-200 rounded-lg">
                  {/* Derive headers once from the first item */}
                  {(() => {
                    const headers = Object.keys(response[0]);
                    return (
                      <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                          <tr>
                            {headers.map((key) => (
                              <th key={key} className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                                {key.replace(/_/g, ' ')}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200">
                          {response.map((item: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50 align-top">
                              {headers.map((key, colIdx) => {
                                const val = item[key];
                                return (
                                  <td key={`${idx}-${colIdx}`} className="px-6 py-4 text-sm text-slate-700">
                                    {/* Custom Rendering Logic */}
                                    {key === 'items' && Array.isArray(val) ? (
                                      <div className="overflow-hidden rounded-md border border-slate-100 bg-slate-50">
                                        <table className="min-w-full text-xs box-border">
                                          <thead className="bg-slate-100">
                                            <tr>
                                              <th className="px-2 py-1 text-left font-medium text-slate-500">Desc</th>
                                              <th className="px-2 py-1 text-right font-medium text-slate-500">Qty</th>
                                              <th className="px-2 py-1 text-right font-medium text-slate-500">Amt</th>
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-slate-100">
                                            {val.map((subItem: any, subIdx: number) => (
                                              <tr key={subIdx}>
                                                <td className="px-2 py-1">{subItem.description || '-'}</td>
                                                <td className="px-2 py-1 text-right">{subItem.quantity}</td>
                                                <td className="px-2 py-1 text-right font-mono">
                                                  {subItem.amount ? `₹${subItem.amount}` : '-'}
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    ) : key === 'bill_date' && val ? (
                                      <span className="whitespace-nowrap">
                                        {new Date(val).toLocaleDateString()}
                                      </span>
                                    ) : (key === 'total_amount' || key === 'amount') && typeof val === 'number' ? (
                                      <span className="font-mono font-medium">
                                        ₹{val.toLocaleString('en-IN')}
                                      </span>
                                    ) : (
                                      <span>{typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val ?? '-')}</span>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    );
                  })()}
                </div>
              ) : typeof response === 'string' ? (
                <div className="prose prose-indigo max-w-none text-slate-800 leading-relaxed mb-6">
                  {response}
                </div>
              ) : null}

              {/* Always show JSON Code View at the bottom */}
              <details className="group">
                <summary className="list-none flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-400 hover:text-indigo-600 transition-colors mb-2 select-none">
                  <svg className="w-4 h-4 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
                  View Raw JSON Response
                </summary>
                <div className="relative animate-in slide-in-from-top-2 fade-in duration-200">
                  <pre className="text-xs font-mono text-slate-600 bg-slate-50 p-4 rounded-lg overflow-x-auto border border-slate-200 shadow-inner">
                    {JSON.stringify(response, null, 2)}
                  </pre>
                  <div className="absolute top-2 right-2 text-[10px] text-slate-400 font-sans px-1.5 py-0.5 bg-white rounded border border-slate-200 opacity-70">
                    JSON
                  </div>
                </div>
              </details>
            </div>
          </div>
        </div>
      )}

      {!response && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 px-8 opacity-60">
          {['Highest vendor last month?', 'Total spent on food?', 'List all bills from Jan 2024', 'Show me bills > $100'].map((placeholder, i) => (
            <button
              key={i}
              onClick={() => setQuery(placeholder)}
              className="p-4 rounded-xl border-2 border-dashed border-slate-200 hover:border-indigo-300 hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 transition-all text-left text-sm font-medium"
            >
              "{placeholder}"
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
