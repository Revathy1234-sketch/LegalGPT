import { FileText, MoreHorizontal } from "lucide-react";

const DEMO_CONTRACTS = [
  { id: 1, name: "Master Services Agreement", type: "MSA", date: "Oct 24, 2023", status: "Ready", risk: "Low", lastAnalysis: "2 hrs ago" },
  { id: 2, name: "Non-Disclosure Agreement", type: "NDA", date: "Oct 23, 2023", status: "Processing", risk: "Medium", lastAnalysis: "In Progress" },
  { id: 3, name: "Software Licensing Agreement", type: "License", date: "Oct 20, 2023", status: "Needs Review", risk: "High", lastAnalysis: "1 day ago" },
  { id: 4, name: "Vendor Agreement", type: "Vendor", date: "Oct 19, 2023", status: "Ready", risk: "Low", lastAnalysis: "3 days ago" },
];

export function RecentContracts() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-5 sm:p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Recent Contracts</h2>
          <p className="text-sm text-slate-500 mt-1">Latest documents uploaded to the workspace.</p>
        </div>
        <button className="text-sm text-blue-600 font-medium hover:text-blue-700 self-start sm:self-auto">View All</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left whitespace-nowrap">
          <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 font-medium">Contract</th>
              <th className="px-6 py-3 font-medium">Type</th>
              <th className="px-6 py-3 font-medium">Uploaded</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Risk</th>
              <th className="px-6 py-3 font-medium">Last Analysis</th>
              <th className="px-6 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {DEMO_CONTRACTS.map((contract) => (
              <tr key={contract.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50/50 text-blue-600 rounded-md border border-blue-100">
                      <FileText className="h-4 w-4" />
                    </div>
                    <span className="font-medium text-slate-900">{contract.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-600">{contract.type}</td>
                <td className="px-6 py-4 text-slate-600">{contract.date}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                    contract.status === 'Ready' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    contract.status === 'Processing' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {contract.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                    contract.risk === 'Low' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    contract.risk === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                    'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {contract.risk}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-600">{contract.lastAnalysis}</td>
                <td className="px-6 py-4 text-right">
                  <button className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors outline-none focus:ring-2 focus:ring-slate-200">
                    <MoreHorizontal className="h-5 w-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
