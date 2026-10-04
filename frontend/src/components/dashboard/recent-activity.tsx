import { CheckCircle2, FileUp, AlertTriangle, Scale, GitCompare, Info } from "lucide-react";
import { RecentActivity as RecentActivityType } from "@/src/lib/api/dashboard";

interface Props {
  activities: RecentActivityType[];
}

export function RecentActivity({ activities }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col h-[380px]">
      <div className="mb-4 shrink-0">
        <h2 className="text-lg font-semibold text-slate-900">Recent Activity</h2>
        <p className="text-sm text-slate-700/60 mt-1">Latest actions in your workspace.</p>
      </div>
      <div className="flex-1 overflow-y-auto pr-2 space-y-5 custom-scrollbar">
        {activities.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-700/60 text-sm">No recent activity.</div>
        ) : (
          activities.map((activity) => {
            const Icon = activity.type === 'upload' ? FileUp :
                         activity.type === 'risk' ? AlertTriangle :
                         activity.type === 'clause' ? Scale :
                         activity.type === 'compare' ? GitCompare :
                         activity.type === 'negotiation' ? CheckCircle2 : Info;
            return (
              <div key={activity.id} className="flex gap-4">
                <div className={`mt-0.5 p-2 rounded-full h-8 w-8 flex items-center justify-center shrink-0 border ${
                  activity.type === 'upload' ? 'bg-blue-50 text-blue-600 border-blue-100' :
                  activity.type === 'risk_analysis' || activity.type === 'compliance_check' ? 'bg-amber-50 text-amber-600 border-amber-100' :
                  activity.type === 'clause_extraction' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' :
                  activity.type === 'comparison' ? 'bg-purple-50 text-purple-600 border-purple-100' :
                  'bg-emerald-50 text-emerald-600 border-emerald-100'
                }`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">{activity.title}</p>
                  <p className="text-sm text-slate-700/80 mt-0.5">{activity.target}</p>
                  <p className="text-xs text-slate-700/40 mt-1.5">{activity.time}</p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
