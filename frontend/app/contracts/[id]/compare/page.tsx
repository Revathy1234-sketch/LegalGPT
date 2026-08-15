"use client";

import { use, useState } from "react";
import { GitCompare, ArrowRight, MinusCircle, PlusCircle, AlertCircle, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import { contractsApi } from "@/lib/api/contracts";

export default function ContractCompare({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [targetId, setTargetId] = useState<string>("");

  const { data: baseContract } = useQuery({
    queryKey: ['contract', resolvedParams.id],
    queryFn: () => contractsApi.getById(resolvedParams.id),
  });

  const { data: contracts } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll(),
  });

  const availableTargets = contracts?.filter(c => c.id !== resolvedParams.id) || [];

  const { data: comparison, isLoading, isError } = useQuery({
    queryKey: ['compare', resolvedParams.id, targetId],
    queryFn: () => analysisApi.compare({ contract_a_id: resolvedParams.id, contract_b_id: targetId }),
    enabled: !!targetId,
  });

  const differences = comparison?.differences || [];

  const parsedDifferences = differences.map((d: string) => {
    try {
      const parsed = typeof d === 'string' ? JSON.parse(d.replace(/'/g, '"')) : d;
      return {
        type: parsed.type || 'modified',
        base_text: parsed.contract_a || parsed.base_text || (typeof d === 'string' ? d : ''),
        target_text: parsed.contract_b || parsed.target_text || '',
      };
    } catch {
      return { type: 'modified', base_text: String(d), target_text: '' };
    }
  });

  return (
    <div className="space-y-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Contract Comparison</h2>
          <p className="text-slate-500 mt-1 font-medium">Visual diff between the current agreement and a previous version.</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-4 p-5 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex-1 w-full p-4 bg-slate-50 rounded-lg border border-slate-200">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">Base Document</span>
          <p className="font-bold text-slate-900 truncate">{baseContract?.file_name || "Loading..."}</p>
        </div>
        <ArrowRight className="h-5 w-5 text-slate-400 shrink-0 rotate-90 sm:rotate-0" />
        <div className="flex-1 w-full p-4 bg-blue-50/50 rounded-lg border border-blue-200">
          <span className="text-xs font-bold text-blue-500 uppercase tracking-widest block mb-1.5">Target Document</span>
          <select
            className="w-full bg-transparent font-bold text-blue-900 outline-none cursor-pointer truncate"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
          >
            <option value="" disabled>Select a contract to compare...</option>
            {availableTargets.map(t => (
              <option key={t.id} value={t.id}>{t.file_name}</option>
            ))}
          </select>
        </div>
      </div>

      {targetId ? (
        <>
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200 shadow-sm">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
              <p>Analyzing differences...</p>
            </div>
          ) : isError ? (
            <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600 shadow-sm">
              Failed to load comparison.
            </div>
          ) : differences.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200 shadow-sm">
              <p>No significant differences found.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-500">Added Clauses</p>
                    <p className="text-2xl font-bold text-emerald-600 mt-1">
                      {parsedDifferences.filter((d) => d.type === 'added').length}
                    </p>
                  </div>
                  <PlusCircle className="h-8 w-8 text-emerald-100" />
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-500">Removed Clauses</p>
                    <p className="text-2xl font-bold text-rose-600 mt-1">
                      {parsedDifferences.filter((d) => d.type === 'removed').length}
                    </p>
                  </div>
                  <MinusCircle className="h-8 w-8 text-rose-100" />
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-500">Modified Clauses</p>
                    <p className="text-2xl font-bold text-amber-600 mt-1">
                      {parsedDifferences.filter((d) => d.type === 'modified').length}
                    </p>
                  </div>
                  <AlertCircle className="h-8 w-8 text-amber-100" />
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50 flex items-center gap-3">
                  <GitCompare className="h-5 w-5 text-slate-500" />
                  <h3 className="font-bold text-slate-900">Important Differences</h3>
                </div>

                <div className="divide-y divide-slate-100">
                  {parsedDifferences.map((diff, idx: number) => (
                    <div key={idx} className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-rose-50/30 rounded-lg border border-rose-100 p-5">
                        <h4 className="text-xs font-bold text-rose-600 uppercase tracking-widest mb-3">Base Document</h4>
                        <p className={`text-sm text-slate-700 font-serif leading-relaxed ${diff.type === 'removed' ? 'line-through decoration-rose-400 decoration-2' : ''}`}>
                          {diff.base_text || "N/A"}
                        </p>
                      </div>
                      <div className="bg-emerald-50/30 rounded-lg border border-emerald-100 p-5">
                        <h4 className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3">Target Document</h4>
                        <p className={`text-sm text-slate-700 font-serif leading-relaxed ${diff.type === 'added' ? 'bg-emerald-200/50 rounded px-1.5 py-0.5 text-emerald-900 font-medium border border-emerald-200' : ''}`}>
                          {diff.target_text || "N/A"}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500 bg-slate-50 rounded-xl border border-slate-200 border-dashed">
          <GitCompare className="h-12 w-12 text-slate-300 mb-4" />
          <p>Select a target document above to begin comparison.</p>
        </div>
      )}
    </div>
  );
}
