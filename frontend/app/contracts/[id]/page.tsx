"use client";

import { use } from "react";
import { FileText, AlertTriangle, Scale, Clock, Loader2 } from "lucide-react";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RiskOverview } from "@/src/components/dashboard/risk-overview";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/src/lib/api/analysis";

export default function ContractOverview({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['summary', resolvedParams.id],
    queryFn: () => analysisApi.summarize(resolvedParams.id),
  });

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Contract Overview</h2>
        <p className="text-slate-500 mt-1 font-medium">High-level summary and metrics for this document.</p>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
          <p>Analyzing contract...</p>
        </div>
      ) : isError ? (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
          Failed to load contract overview.
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total Clauses"
              value={data.clauses?.length || 0}
              icon={<FileText className="h-5 w-5" />}
            />
            <StatCard
              title="Risk Score"
              value={data.risk_analysis?.overall_score || 0}
              icon={<AlertTriangle className="h-5 w-5" />}
            />
            <StatCard
              title="Obligations"
              value={0}
              icon={<Scale className="h-5 w-5" />}
            />
            <StatCard
              title="Key Dates"
              value={0}
              icon={<Clock className="h-5 w-5" />}
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Executive Summary</h3>
              <div className="prose prose-sm prose-slate max-w-none text-slate-600 leading-relaxed font-serif whitespace-pre-wrap">
                {data.summary || "No summary available."}
              </div>
            </div>
            {/* Calculate distribution for this specific contract if available */}
            <RiskOverview data={
              data.risk_analysis?.risk_matrix ? (
                (() => {
                  let h = 0, m = 0, l = 0;
                  const h_f: any[] = [];
                  const m_f: any[] = [];
                  const l_f: any[] = [];
                  const matrix = data.risk_analysis.risk_matrix as any[];
                  matrix.forEach((r: any) => {
                    const sev = r.severity?.toLowerCase() || r.risk_level?.toLowerCase() || '';
                    const finding = {
                        category: r.category || "General",
                        description: r.description || "",
                        impact: r.impact || "",
                        evidence: r.evidence || ""
                    };
                    if (sev === 'high' || sev === 'critical') { h++; h_f.push(finding); }
                    else if (sev === 'medium') { m++; m_f.push(finding); }
                    else { l++; l_f.push(finding); }
                  });
                  return [
                    { name: 'High Risk', value: h, color: '#f43f5e', findings: h_f },
                    { name: 'Medium Risk', value: m, color: '#f59e0b', findings: m_f },
                    { name: 'Low Risk', value: l, color: '#10b981', findings: l_f }
                  ];
                })()
              ) : []
            } />
          </div>
        </>
      ) : null}
    </div>
  );
}
