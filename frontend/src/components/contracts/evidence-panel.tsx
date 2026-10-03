import { FileText, Database, Info, ExternalLink, X, ShieldAlert } from "lucide-react";
import { useEvidence } from "@/src/contexts/evidence-context";

export function EvidencePanel() {
  const { evidence, sourceType, isOpen, setIsOpen } = useEvidence();

  if (!isOpen && evidence.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-slate-400 text-sm">
        <Database className="h-10 w-10 text-slate-200 mb-3" />
        <p className="text-center">Select an item to view its supporting evidence.</p>
      </div>
    );
  }

  return (
    <>
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Evidence Panel</h2>
        </div>
        <button 
          onClick={() => setIsOpen(false)}
          className="text-slate-400 hover:text-slate-600 rounded-md p-1 hover:bg-slate-200/50 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Current Source</h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
              {sourceType}
            </span>
          </div>

          {evidence.length === 0 ? (
            <div className="text-sm text-slate-500 italic p-4 bg-slate-50 rounded-lg border border-slate-100">
              No specific evidence found for this selection.
            </div>
          ) : (
            evidence.map((item, index) => (
              <div key={item.id || index} className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
                <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-rose-500" />
                    <span className="text-sm font-bold text-slate-900">{item.finding || "Analysis"}</span>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase ${
                    item.severity?.toLowerCase().includes('high') ? 'bg-rose-50 text-rose-700 border-rose-200' :
                    item.severity?.toLowerCase().includes('low') ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {item.severity || "MEDIUM"}
                  </span>
                </div>
                {item.explanation && (
                  <div className="p-3 bg-slate-50 border-b border-slate-100">
                    <h4 className="text-xs font-bold text-slate-500 uppercase mb-1 tracking-wider">Why</h4>
                    <p className="text-sm text-slate-700">{item.explanation}</p>
                  </div>
                )}
                <div className="p-3 flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Source</h4>
                    <span className="text-xs font-medium text-slate-500">{item.page} · {item.section}</span>
                  </div>
                  <div className="p-3 bg-blue-50/50 rounded border border-blue-100 relative group">
                    <p className="text-sm text-slate-700 font-serif leading-relaxed italic">
                      "{item.sourceText}"
                    </p>
                  </div>
                </div>
                <div className="p-2 border-t border-slate-100 bg-slate-50 flex justify-end">
                  <button className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors">
                    View in Document <ExternalLink className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="rounded-lg bg-blue-50 border border-blue-100 p-3 mt-auto">
          <div className="flex gap-2">
            <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <p className="text-xs text-blue-800 leading-relaxed">
              The AI generated its response based on the evidence shown above. Evidence is grounded entirely in the uploaded contract.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
