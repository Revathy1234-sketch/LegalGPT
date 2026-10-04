"use client";

import { useState } from "react";
import { AppShell } from "@/src/components/layout/app-shell";
import { EvidenceProvider, useEvidence } from "@/src/contexts/evidence-context";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { ContractOverviewView } from "@/src/components/contracts/contract-overview-view";
import { contractsApi, ContractResponse } from "@/lib/api/contracts";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, FileText, Loader2 } from "lucide-react";

function OverviewEvidenceWrapper() {
  const { isOpen } = useEvidence();
  if (!isOpen) return null;
  return (
    <div className="w-80 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hidden xl:flex flex-col shrink-0 relative z-10 shadow-xl m-4 rounded-xl overflow-hidden h-[calc(100vh-8rem)] min-h-0 sticky top-4">
      <EvidencePanel />
    </div>
  );
}

function OverviewContent() {
  // Empty state = fall back to the user's most recent contract (derived, no effects).
  const [selectedId, setSelectedId] = useState<string>("");

  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts"],
    queryFn: contractsApi.getAll,
  });

  const effectiveId = selectedId || contracts?.[0]?.id || "";

  return (
    <div className="flex h-full w-full">
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Contract Overview</h1>
            <p className="text-slate-700/60 mt-1 sm:mt-1.5 font-medium">
              Executive summary, risk distribution and PDF proof — in one place.
            </p>
          </div>

          <div className="relative">
            <select
              value={effectiveId}
              onChange={(e) => setSelectedId(e.target.value)}
              disabled={isLoading || !contracts?.length}
              className="appearance-none bg-white border border-slate-200 text-slate-900/90 text-sm rounded-lg pl-9 pr-9 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer font-medium shadow-sm disabled:opacity-60"
            >
              {isLoading ? (
                <option>Loading contracts…</option>
              ) : !contracts?.length ? (
                <option>No contracts yet — upload one first</option>
              ) : (
                contracts.map((c: ContractResponse) => (
                  <option key={c.id} value={c.id}>{c.file_name}</option>
                ))
              )}
            </select>
            <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700/40 pointer-events-none" />
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700/40 pointer-events-none" />
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-700/60">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
            <p>Loading your contracts…</p>
          </div>
        ) : !contracts?.length ? (
          <div className="bg-white rounded-xl border border-dashed border-slate-200/80 p-10 text-center text-slate-700/60">
            <FileText className="h-10 w-10 mx-auto text-slate-300 mb-3" />
            <p className="font-medium text-slate-700">No contracts uploaded yet</p>
            <p className="text-sm mt-1">Upload a contract first, then come back for its overview.</p>
          </div>
        ) : effectiveId ? (
          <ContractOverviewView contractId={effectiveId} />
        ) : null}
      </div>

      <OverviewEvidenceWrapper />
    </div>
  );
}

export default function ContractOverviewPage() {
  return (
    <EvidenceProvider>
      <AppShell>
        <OverviewContent />
      </AppShell>
    </EvidenceProvider>
  );
}
