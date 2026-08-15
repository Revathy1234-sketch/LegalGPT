import { AppShell } from "@/src/components/layout/app-shell";
import { Search, Filter, MoreHorizontal, FileText, CheckCircle2, Bot, Scale, ShieldAlert, GitCompare } from "lucide-react";
import Link from "next/link";

export default function AnalysisHistory() {
  const history = [
    { id: 1, contract: "Master Services Agreement", type: "Contract Insight", status: "Completed", risk: "Low", date: "Oct 24, 2023 10:30 AM", icon: FileText },
    { id: 2, contract: "Non-Disclosure Agreement", type: "Risk Analysis", status: "Processing", risk: "Medium", date: "Oct 24, 2023 09:15 AM", icon: ShieldAlert },
    { id: 3, contract: "Software Licensing Agreement", type: "Clause Intelligence", status: "Completed", risk: "High", date: "Oct 23, 2023 04:20 PM", icon: Scale },
    { id: 4, contract: "Vendor Agreement vs MSA v2", type: "Contract Compare", status: "Completed", risk: "Low", date: "Oct 22, 2023 11:10 AM", icon: GitCompare },
    { id: 5, contract: "Employment Contract", type: "Contract Chat", status: "Completed", risk: "Low", date: "Oct 20, 2023 02:45 PM", icon: Bot },
  ];

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Analysis History</h1>
          <p className="text-slate-500 mt-1 font-medium">Log of all AI operations and manual reviews.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search history..."
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-slate-50 focus:bg-white"
              />
            </div>
            <button className="p-2 border border-slate-200 text-slate-600 rounded-md hover:bg-slate-50 transition-colors shrink-0 outline-none focus:ring-2 focus:ring-slate-300">
              <Filter className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 font-medium">Contract</th>
                <th className="px-6 py-3 font-medium">Analysis Type</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Date</th>
                <th className="px-6 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {history.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4 font-semibold text-slate-900">
                    <Link href="/contracts/1" className="hover:text-blue-600 transition-colors">{item.contract}</Link>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-700">
                      <item.icon className="h-4 w-4 text-slate-400" />
                      <span className="font-semibold">{item.type}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border shadow-sm ${
                      item.status === 'Completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                      'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>
                      {item.status === 'Completed' && <CheckCircle2 className="h-3 w-3" />}
                      {item.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500 font-medium">{item.date}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-slate-400 hover:text-slate-600 p-1.5 rounded-md hover:bg-slate-200 transition-colors outline-none focus:ring-2 focus:ring-slate-300">
                      <MoreHorizontal className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
