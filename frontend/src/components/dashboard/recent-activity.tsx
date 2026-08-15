import { CheckCircle2, FileUp, AlertTriangle, Scale, GitCompare } from "lucide-react";

const DEMO_ACTIVITIES = [
  { id: 1, title: "Contract uploaded", target: "Master Services Agreement", time: "2 hours ago", icon: FileUp, type: "upload" },
  { id: 2, title: "Risk analysis completed", target: "Non-Disclosure Agreement", time: "4 hours ago", icon: AlertTriangle, type: "risk" },
  { id: 3, title: "Clause analysis completed", target: "Software Licensing Agreement", time: "1 day ago", icon: Scale, type: "clause" },
  { id: 4, title: "Contract comparison completed", target: "Vendor Agreement vs MSA v2", time: "2 days ago", icon: GitCompare, type: "compare" },
  { id: 5, title: "Negotiation analysis completed", target: "Partner Agreement", time: "3 days ago", icon: CheckCircle2, type: "negotiation" },
];

export function RecentActivity() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col h-[380px]">
      <div className="mb-4 shrink-0">
        <h2 className="text-lg font-semibold text-slate-900">Recent Activity</h2>
        <p className="text-sm text-slate-500 mt-1">Latest actions in your workspace.</p>
      </div>
      <div className="flex-1 overflow-y-auto pr-2 space-y-5 custom-scrollbar">
        {DEMO_ACTIVITIES.map((activity) => (
          <div key={activity.id} className="flex gap-4">
            <div className={`mt-0.5 p-2 rounded-full h-8 w-8 flex items-center justify-center shrink-0 border ${
              activity.type === 'upload' ? 'bg-blue-50 text-blue-600 border-blue-100' :
              activity.type === 'risk' ? 'bg-amber-50 text-amber-600 border-amber-100' :
              activity.type === 'clause' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' :
              activity.type === 'compare' ? 'bg-purple-50 text-purple-600 border-purple-100' :
              'bg-emerald-50 text-emerald-600 border-emerald-100'
            }`}>
              <activity.icon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900">{activity.title}</p>
              <p className="text-sm text-slate-600 mt-0.5">{activity.target}</p>
              <p className="text-xs text-slate-400 mt-1.5">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
