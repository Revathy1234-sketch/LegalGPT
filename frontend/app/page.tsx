"use client";

import { AppShell } from "@/src/components/layout/app-shell";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RecentContracts } from "@/src/components/dashboard/recent-contracts";
import { RecentActivity } from "@/src/components/dashboard/recent-activity";
import { RiskDistributionChart } from "@/src/components/dashboard/risk-distribution";
import { QuickActions } from "@/src/components/dashboard/quick-actions";
import { FileText, AlertTriangle, Clock, CheckCircle2, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/src/lib/api/dashboard";
import Link from "next/link";
import { EvidenceProvider } from "@/src/contexts/evidence-context";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { useEvidence } from "@/src/contexts/evidence-context";

function DashboardEvidenceWrapper() {
  const { isOpen } = useEvidence();
  if (!isOpen) return null;
  return (
    <div className="w-80 border-l border-slate-200 bg-white hidden xl:flex flex-col shrink-0 relative z-10 shadow-[-4px_0_15px_-3px_rgba(0,0,0,0.02)]">
      <EvidencePanel />
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard_stats'],
    queryFn: dashboardApi.getStats,
    retry: 1,
  });

  return (
    <EvidenceProvider>
      <AppShell>
        <div className="flex h-full w-full">
          <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Welcome to LegalGPT</h1>
                <p className="text-slate-700/60 mt-1 sm:mt-1.5 font-medium">Explainable Multi-Agent Contract Intelligence</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/agents" className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 hover:text-slate-900 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-slate-200">
                  Open Agent Workspace
                </Link>
                <Link href="/contracts/upload" className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
                  Upload Contract
                </Link>
              </div>
            </div>

            <QuickActions />

            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-700/60">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
                <p>Loading dashboard…</p>
              </div>
            ) : isError ? (
              <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
                Failed to load dashboard statistics — the backend may be restarting. This panel refreshes automatically.
              </div>
            ) : data ? (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                  <StatCard
                    title="Total Contracts"
                    value={data.stats.total_contracts}
                    icon={<FileText className="h-5 w-5" />}
                  />
                  <StatCard
                    title="High Risk"
                    value={data.stats.high_risk}
                    icon={<AlertTriangle className="h-5 w-5" />}
                  />
                  <StatCard
                    title="Pending Analysis"
                    value={data.stats.pending_analysis}
                    icon={<Clock className="h-5 w-5" />}
                  />
                  <StatCard
                    title="Completed Analyses"
                    value={data.stats.completed_analyses}
                    icon={<CheckCircle2 className="h-5 w-5" />}
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <RiskDistributionChart
                    data={data.risk_distribution}
                    height={420}
                    statusDistribution={data.status_distribution}
                    contractTypes={data.contract_types}
                    riskRadar={data.risk_radar}
                    agentUsage={data.agent_usage}
                  />
                  <RecentActivity activities={data.recent_activity} />
                </div>

                <div className="w-full">
                  <RecentContracts contracts={data.recent_contracts} />
                </div>
              </>
            ) : null}
          </div>
          <DashboardEvidenceWrapper />
        </div>
      </AppShell>
    </EvidenceProvider>
  );
}
