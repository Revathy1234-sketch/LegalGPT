"use client";

import { use } from "react";
import { Search, ChevronDown, CheckCircle2, AlertTriangle, ShieldAlert, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";

export default function Clauses({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['clauses', resolvedParams.id],
    queryFn: () => analysisApi.clauses(resolvedParams.id),
  });

  const clauses = data?.clauses || [];

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Clause Intelligence</h2>
        <p className="text-slate-500 mt-1 font-medium">Categorized and analyzed clauses from the document.</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <button className="px-3 py-1.5 bg-slate-100 text-slate-900 rounded-md text-sm font-medium">All Clauses</button>
            <button className="px-3 py-1.5 text-slate-600 hover:bg-slate-50 rounded-md text-sm font-medium transition-colors">High Risk</button>
            <button className="px-3 py-1.5 text-slate-600 hover:bg-slate-50 rounded-md text-sm font-medium transition-colors">Non-Standard</button>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search clauses..."
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-slate-50 focus:bg-white"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 font-medium">Clause Name</th>
                <th className="px-6 py-3 font-medium">Category</th>
                <th className="px-6 py-3 font-medium">Risk Level</th>
                <th className="px-6 py-3 font-medium">AI Confidence</th>
                <th className="px-6 py-3 font-medium">Source</th>
                <th className="px-6 py-3 font-medium text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
                    Analyzing clauses...
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-rose-500">
                    Failed to analyze clauses.
                  </td>
                </tr>
              ) : clauses.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    No clauses found.
                  </td>
                </tr>
              ) : (
                clauses.map((clause, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900">{clause.title}</td>
                    <td className="px-6 py-4 text-slate-600">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                        {clause.category}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        clause.confidence_score > 0.9 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        clause.confidence_score > 0.7 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                        'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {clause.confidence_score > 0.9 && <CheckCircle2 className="h-3 w-3" />}
                        {clause.confidence_score <= 0.9 && clause.confidence_score > 0.7 && <AlertTriangle className="h-3 w-3" />}
                        {clause.confidence_score <= 0.7 && <ShieldAlert className="h-3 w-3" />}
                        {clause.confidence_score > 0.9 ? 'Low' : clause.confidence_score > 0.7 ? 'Medium' : 'High'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-medium">{(clause.confidence_score * 100).toFixed(0)}%</td>
                    <td className="px-6 py-4 text-blue-600 font-medium hover:underline cursor-pointer">View</td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-slate-400 hover:text-slate-600 p-1.5 rounded-md hover:bg-slate-200 transition-colors outline-none focus:ring-2 focus:ring-slate-300">
                        <ChevronDown className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
