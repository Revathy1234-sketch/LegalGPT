import { FileText, AlertTriangle, Scale, Clock } from "lucide-react";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RiskOverview } from "@/src/components/dashboard/risk-overview";

export default function ContractOverview() {
  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Contract Overview</h2>
        <p className="text-slate-500 mt-1 font-medium">High-level summary and metrics for this document.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Clauses"
          value={42}
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          title="High Risk Clauses"
          value={3}
          icon={<AlertTriangle className="h-5 w-5" />}
          trend={{ value: "Action required", isPositive: false }}
        />
        <StatCard
          title="Obligations"
          value={15}
          icon={<Scale className="h-5 w-5" />}
        />
        <StatCard
          title="Key Dates"
          value={4}
          icon={<Clock className="h-5 w-5" />}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Executive Summary</h3>
          <div className="prose prose-sm prose-slate max-w-none text-slate-600 leading-relaxed font-serif">
            <p className="mb-4">
              This Master Services Agreement outlines the terms under which the Service Provider will deliver consulting services to the Client. The agreement establishes a framework for future statements of work (SOWs) and governs intellectual property rights, confidentiality, and liability limitations.
            </p>
            <p>
              The contract generally follows standard market practices, but includes a heavily negotiated limitation of liability clause that caps damages at 2x the annual fees. The confidentiality provisions are mutual and survive for 5 years post-termination.
            </p>
          </div>
        </div>
        <RiskOverview />
      </div>
    </div>
  );
}
