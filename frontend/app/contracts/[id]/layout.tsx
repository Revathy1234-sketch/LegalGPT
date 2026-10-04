"use client";

import { ReactNode, use } from "react";
import { Topbar } from "@/src/components/layout/topbar";
import { Sidebar } from "@/src/components/layout/sidebar";
import { ContractNavigation } from "@/src/components/contracts/contract-navigation";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { useQuery } from "@tanstack/react-query";
import { contractsApi } from "@/lib/api/contracts";
import { EvidenceProvider, useEvidence } from "@/src/contexts/evidence-context";
import { EvidenceToggle } from "@/src/components/contracts/evidence-toggle";
import { riskLevel, riskBadgeClass } from "@/src/lib/risk-utils";

export default function ContractLayout({ children, params }: { children: ReactNode, params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data: contract, isLoading, isError } = useQuery({
    queryKey: ['contract', resolvedParams.id],
    queryFn: () => contractsApi.getById(resolvedParams.id),
  });
  return (
    <EvidenceProvider>
      <div className="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden selection:bg-blue-100 selection:text-blue-900">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar />

        {/* Workspace specific header */}
        <div className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-4 sm:px-6 shrink-0">
          <div className="flex items-center gap-3">
            {isLoading ? (
              <div className="h-5 bg-slate-200 rounded w-48 animate-pulse"></div>
            ) : isError ? (
              <h1 className="text-lg font-bold text-rose-600">Failed to load contract</h1>
            ) : (
              <>
                <h1 className="text-lg font-bold text-slate-900 truncate max-w-[200px] sm:max-w-md">
                  {contract?.file_name}
                </h1>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  {contract?.status}
                </span>
                {contract?.risk_analysis && (
                  <span className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${
                    riskBadgeClass(riskLevel(contract.risk_analysis.overall_score))
                  }`}>
                    {riskLevel(contract.risk_analysis.overall_score)} Risk · {contract.risk_analysis.overall_score}/100
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Left Navigation */}
          <div className="w-56 border-r border-slate-200 bg-slate-50/50 hidden md:block shrink-0 overflow-y-auto">
            <ContractNavigation contractId={resolvedParams.id} />
          </div>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto bg-slate-50 relative">
            <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto w-full">
              {children}
            </div>
          </main>

          {/* Right Evidence Panel — hidden/shown by the floating toggle */}
          <ContractEvidenceColumn />
        </div>
      </div>
      <EvidenceToggle />
    </div>
    </EvidenceProvider>
  );
}

function ContractEvidenceColumn() {
  const { isOpen } = useEvidence();
  if (!isOpen) return null;
  return (
    <div className="w-80 border-l border-slate-200 bg-white hidden lg:flex flex-col shrink-0 relative z-10 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.02)]">
      <EvidencePanel />
    </div>
  );
}
