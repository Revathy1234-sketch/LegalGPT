import { AppShell } from "@/src/components/layout/app-shell";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RecentContracts } from "@/src/components/dashboard/recent-contracts";
import { RiskOverview } from "@/src/components/dashboard/risk-overview";
import { RecentActivity } from "@/src/components/dashboard/recent-activity";
import { QuickActions } from "@/src/components/dashboard/quick-actions";
import { FileText, AlertTriangle, Clock, CheckCircle2 } from "lucide-react";

export default function Dashboard() {
  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Welcome to LegalGPT</h1>
          <p className="text-slate-500 mt-1 sm:mt-1.5 font-medium">Explainable Multi-Agent Contract Intelligence</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 hover:text-slate-900 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-slate-200">
            Open AI Workspace
          </button>
          <button className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
            Upload Contract
          </button>
        </div>
      </div>

      <QuickActions />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatCard
          title="Total Contracts"
          value={24}
          icon={<FileText className="h-5 w-5" />}
          trend={{ value: "12% this month", isPositive: true }}
        />
        <StatCard
          title="High Risk"
          value={6}
          icon={<AlertTriangle className="h-5 w-5" />}
          trend={{ value: "2 from last week", isPositive: false }}
        />
        <StatCard
          title="Pending Analysis"
          value={3}
          icon={<Clock className="h-5 w-5" />}
        />
        <StatCard
          title="Completed Analyses"
          value={41}
          icon={<CheckCircle2 className="h-5 w-5" />}
          trend={{ value: "8 this week", isPositive: true }}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <RecentContracts />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-1 gap-6">
          <RiskOverview />
          <RecentActivity />
        </div>
      </div>
    </AppShell>
  );
}
