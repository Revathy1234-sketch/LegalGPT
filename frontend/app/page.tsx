"use client";

import { AppShell } from "@/src/components/layout/app-shell";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RecentContracts } from "@/src/components/dashboard/recent-contracts";
import { RiskOverview } from "@/src/components/dashboard/risk-overview";
import { RecentActivity } from "@/src/components/dashboard/recent-activity";
import { QuickActions } from "@/src/components/dashboard/quick-actions";
import { FileText, AlertTriangle, Clock, CheckCircle2, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/src/lib/api/dashboard";
import Link from "next/link";

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard_stats'],
    queryFn: dashboardApi.getStats,
  });

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Welcome to LegalGPT</h1>
          <p className="text-slate-500 mt-1 sm:mt-1.5 font-medium">Explainable Multi-Agent Contract Intelligence</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/contracts" className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 hover:text-slate-900 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-slate-200">
            Open AI Workspace
          </Link>
          <Link href="/contracts/upload" className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
            Upload Contract
          </Link>
        </div>
      </div>

      <QuickActions />

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
          <p>Loading dashboard...</p>
        </div>
      ) : isError ? (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
          Failed to load dashboard statistics.
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

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2">
              <RecentContracts contracts={data.recent_contracts} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-6">
              <RiskOverview data={data.risk_distribution} />
              <RecentActivity activities={data.recent_activity} />
            </div>
          </div>
        </>
      ) : null}
    </AppShell>
  );
}
