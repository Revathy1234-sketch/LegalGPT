"use client";

import { use, useEffect, useRef } from "react";
import { ShieldCheck, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import { useEvidence } from "@/src/contexts/evidence-context";
import { evidenceFromCompliance } from "@/src/lib/evidence-mapper";

export default function Compliance({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const evidence = useEvidence();
  const loadedFor = useRef<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['compliance', resolvedParams.id],
    queryFn: () => analysisApi.compliance(resolvedParams.id),
  });

  // Automatic evidence for the Compliance agent.
  useEffect(() => {
    if (!data || loadedFor.current === resolvedParams.id) return;
    loadedFor.current = resolvedParams.id;
    const items = evidenceFromCompliance(data.issues as unknown as Array<Record<string, unknown>>);
    if (items.length > 0) {
      evidence.setSourceType("Compliance Agent");
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, resolvedParams.id]);

  const issues = data?.issues || [];
  const recommendations = data?.recommendations || [];
  const isCompliant = data?.compliant ?? true;
  return (
    <div className="space-y-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Compliance Status</h2>
          <p className="text-slate-700/60 mt-1 font-medium">Assessment against regulatory frameworks and company policies.</p>
        </div>
        {!isLoading && !isError && (
          <div className={`px-3 py-2 rounded-lg border flex items-center gap-2 shadow-sm ${
            isCompliant ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'
          }`}>
            {isCompliant ? <ShieldCheck className="h-4 w-4 text-emerald-600" /> : <AlertCircle className="h-4 w-4 text-rose-600" />}
            <span className={`text-sm font-semibold ${isCompliant ? 'text-emerald-800' : 'text-rose-800'}`}>
              {isCompliant ? 'Generally Compliant' : 'Non-Compliant Findings'}
            </span>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-700/60">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
          <p>Running compliance checks...</p>
        </div>
      ) : isError ? (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
          Failed to load compliance analysis.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {issues.length === 0 ? (
              <div className="col-span-full bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-700/60 shadow-sm">
                No specific compliance issues found.
              </div>
            ) : issues.map((issue, idx) => {
              const isIssueCompliant = issue.status.toLowerCase() === 'compliant' || issue.status.toLowerCase() === 'passed';
              return (
                <div key={idx} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-lg border ${
                      isIssueCompliant ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-amber-50 text-amber-600 border-amber-100'
                    }`}>
                      {isIssueCompliant ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
                    </div>
                    <h3 className="font-bold text-slate-900">{issue.framework || issue.clause_type}</h3>
                  </div>
                  <p className="text-sm text-slate-700/80 leading-relaxed font-medium">
                    {issue.gap_analysis || issue.status}
                  </p>
                </div>
              );
            })}
          </div>

          {recommendations.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mt-6">
              <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                <h3 className="font-bold text-slate-900">Recommendations</h3>
              </div>
              <div className="p-5 space-y-4">
                <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700">
                  {recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
