"use client";

import { use } from "react";
import { FileText, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";

export default function ContractSummary({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data: contract, isLoading, isError } = useQuery({
    queryKey: ['summary', resolvedParams.id],
    queryFn: () => analysisApi.summarize(resolvedParams.id),
  });
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Contract Summary</h2>
        <p className="text-slate-500 mt-1 font-medium">Detailed extraction of key terms and dates.</p>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
          <p>Generating summary...</p>
        </div>
      ) : isError ? (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
          Failed to load summary.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-500" />
            <h3 className="font-semibold text-slate-900">Executive Summary</h3>
          </div>
          <div className="p-6">
            <div className="prose prose-slate max-w-none whitespace-pre-wrap">
              {contract?.summary || "No summary available for this contract."}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
