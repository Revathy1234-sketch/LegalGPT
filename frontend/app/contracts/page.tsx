"use client";

import { useState } from "react";
import { AppShell } from "@/src/components/layout/app-shell";
import { Search, Filter, Plus, FileText, MoreHorizontal, Loader2, Trash2, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contractsApi, ContractResponse } from "@/src/lib/api/contracts";
import { format } from "date-fns";
import { formatIST } from "@/src/lib/date-utils";
import { riskLevel, riskBadgeClass } from "@/src/lib/risk-utils";

export default function ContractsLibrary() {
  const queryClient = useQueryClient();
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [deleteConfirmContract, setDeleteConfirmContract] = useState<ContractResponse | null>(null);

  const { data: contracts, isLoading, isError } = useQuery({
    queryKey: ['contracts'],
    queryFn: contractsApi.getAll,
  });

  const deleteMutation = useMutation({
    mutationFn: contractsApi.deleteContract,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      setDeleteConfirmContract(null);
    },
    onError: (error) => {
      alert("Failed to delete contract. Please try again.");
    }
  });

  if (isError) {
    return (
      <AppShell>
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600 m-6">
          Failed to load contracts. Please ensure the backend is running.
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Contracts</h1>
          <p className="text-slate-700/60 mt-1 font-medium">Manage, analyze and review your contracts.</p>
        </div>
        <div className="flex gap-3">
          <Link href="/contracts/upload" className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1">
            <Plus className="h-4 w-4" />
            Upload Contract
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <button className="px-3 py-1.5 bg-slate-100 text-slate-900 rounded-md text-sm font-medium">All</button>
            <button className="px-3 py-1.5 text-slate-700/80 hover:bg-slate-50 rounded-md text-sm font-medium transition-colors">Ready</button>
            <button className="px-3 py-1.5 text-slate-700/80 hover:bg-slate-50 rounded-md text-sm font-medium transition-colors">Processing</button>
            <button className="px-3 py-1.5 text-slate-700/80 hover:bg-slate-50 rounded-md text-sm font-medium transition-colors">Needs Review</button>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700/40" />
              <input
                type="text"
                placeholder="Search contracts..."
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-md text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all bg-slate-50 focus:bg-white"
              />
            </div>
            <button className="p-2 border border-slate-200 text-slate-700/80 rounded-md hover:bg-slate-50 transition-colors shrink-0">
              <Filter className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead className="bg-slate-50 text-slate-700/60 font-medium border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 font-medium">Contract</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Uploaded</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Risk</th>
                <th className="px-6 py-3 font-medium">Last Analysis</th>
                <th className="px-6 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-700/60">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
                    Loading contracts...
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-rose-500">
                    Failed to load contracts.
                  </td>
                </tr>
              ) : contracts?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-700/60">
                    No contracts found. Click &quot;Upload Contract&quot; to get started.
                  </td>
                </tr>
              ) : (
                contracts?.map((contract) => (
                  <tr key={contract.id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <Link href={`/contracts/${contract.id}`} className="flex items-center gap-3 group-hover:text-blue-600 transition-colors">
                        <div className="p-2 bg-blue-50/50 text-blue-600 rounded-md border border-blue-100">
                          <FileText className="h-4 w-4" />
                        </div>
                        <span className="font-medium text-slate-900 group-hover:text-blue-600/90">{contract.file_name}</span>
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-slate-700/80">-</td>
                    <td className="px-6 py-4 text-slate-700/80">
                      {contract.created_at ? formatIST(contract.created_at) : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        contract.status.toLowerCase() === 'completed' || contract.status.toLowerCase() === 'ready' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                        contract.status.toLowerCase() === 'pending' || contract.status.toLowerCase() === 'processing' ? 'bg-blue-50 text-blue-600/90 border-blue-200' :
                        'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        {contract.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {contract.risk_analysis ? (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                          riskBadgeClass(riskLevel(contract.risk_analysis.overall_score))
                        }`}>
                          {riskLevel(contract.risk_analysis.overall_score)} · {contract.risk_analysis.overall_score}/100
                        </span>
                      ) : (
                        <span className="text-slate-700/40 text-xs">Unassessed</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-700/80">-</td>
                    <td className="px-6 py-4 text-right relative">
                      <button 
                        onClick={() => setMenuOpenId(menuOpenId === contract.id ? null : contract.id)}
                        className="text-slate-700/40 hover:text-slate-700/80 p-1 rounded-md hover:bg-slate-100 transition-colors outline-none focus:ring-2 focus:ring-slate-200"
                      >
                        <MoreHorizontal className="h-5 w-5" />
                      </button>
                      
                      {menuOpenId === contract.id && (
                        <>
                          <div 
                            className="fixed inset-0 z-10" 
                            onClick={() => setMenuOpenId(null)}
                          />
                          <div className="absolute right-6 top-10 w-40 bg-white rounded-md shadow-lg border border-slate-200 z-20 py-1 overflow-hidden">
                            <Link 
                              href={`/contracts/${contract.id}`}
                              className="flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                            >
                              <ExternalLink className="h-4 w-4" />
                              Open
                            </Link>
                            <button 
                              onClick={() => {
                                setMenuOpenId(null);
                                setDeleteConfirmContract(contract);
                              }}
                              className="flex items-center gap-2 px-4 py-2 text-sm text-rose-600 hover:bg-rose-50 w-full text-left"
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete
                            </button>
                          </div>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-slate-200 flex items-center justify-between text-sm text-slate-700/60">
          <div>Showing {contracts?.length || 0} entries</div>
          <div className="flex gap-1">
            <button className="px-3 py-1 border border-slate-200 rounded-md text-slate-700/40 cursor-not-allowed bg-slate-50">Previous</button>
            <button className="px-3 py-1 border border-blue-600 bg-blue-600 text-white rounded-md font-medium shadow-sm">1</button>
            <button className="px-3 py-1 border border-slate-200 rounded-md text-slate-700/40 cursor-not-allowed bg-slate-50">Next</button>
          </div>
        </div>
      </div>

      {deleteConfirmContract && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 relative">
            <h3 className="text-lg font-bold text-slate-900 mb-2">Delete Contract</h3>
            <p className="text-sm text-slate-700/60 mb-4">
              Are you sure you want to permanently delete the contract <span className="font-semibold text-slate-700">{deleteConfirmContract.file_name}</span>? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end mt-6">
              <button 
                onClick={() => setDeleteConfirmContract(null)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 transition-colors text-sm font-medium disabled:opacity-50"
              >
                Cancel
              </button>
              <button 
                onClick={() => deleteMutation.mutate(deleteConfirmContract.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-rose-600 border border-transparent text-white rounded-md hover:bg-rose-700 transition-colors text-sm font-medium flex items-center gap-2 disabled:opacity-50"
              >
                {deleteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
