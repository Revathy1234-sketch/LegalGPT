import { FileText, MoreHorizontal } from "lucide-react";
import { RecentContract } from "@/src/lib/api/dashboard";
import Link from "next/link";

interface Props {
  contracts: RecentContract[];
}

export function RecentContracts({ contracts }: Props) {
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
            {contracts.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-10 text-center text-slate-500">
                  No contracts uploaded yet.
                </td>
              </tr>
            ) : contracts.map((contract) => (
              <tr key={contract.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50/50 text-blue-600 rounded-md border border-blue-100">
                      <FileText className="h-4 w-4" />
                    </div>
                    <Link href={`/contracts/${contract.id}`} className="font-medium text-slate-900 hover:text-blue-600">{contract.name}</Link>
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-600">{contract.type}</td>
                <td className="px-6 py-4 text-slate-600">{contract.date}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                    contract.status.toLowerCase() === 'processed' || contract.status.toLowerCase() === 'ready' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    contract.status.toLowerCase() === 'processing' || contract.status.toLowerCase() === 'pending' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {contract.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                    contract.risk.toLowerCase() === 'low' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    contract.risk.toLowerCase() === 'medium' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                    'bg-rose-50 text-rose-700 border-rose-200'
                  }`}>
                    {contract.risk}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-600">{contract.lastAnalysis}</td>
                <td className="px-6 py-4 text-right">
                  <Link href={`/contracts/${contract.id}`} className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors outline-none focus:ring-2 focus:ring-slate-200">
                    <MoreHorizontal className="h-5 w-5 inline-block" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
