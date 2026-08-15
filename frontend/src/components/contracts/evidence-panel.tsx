import { FileText, Database, Info, ExternalLink, X } from "lucide-react";

export function EvidencePanel() {
  return (
    <>
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Evidence Panel</h2>
        </div>
        <button className="text-slate-400 hover:text-slate-600 rounded-md p-1 hover:bg-slate-200/50 transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Current Source</h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
              Hybrid Retrieval
            </span>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
            <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5 text-blue-600" />
                <span className="text-sm font-medium text-slate-900">Section 4.2</span>
              </div>
              <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                98% Match
              </span>
            </div>
            <div className="p-4 bg-yellow-50/30">
              <p className="text-sm text-slate-700 leading-relaxed font-serif">
                &quot;Receiving Party agrees to hold all <mark className="bg-yellow-200 text-yellow-900 px-1 rounded">Confidential Information</mark> in strict confidence and not to disclose such Confidential Information to any third parties without the prior written consent of the Disclosing Party, except as required by law.&quot;
              </p>
            </div>
            <div className="p-2 border-t border-slate-100 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
              <span>Page 3, Paragraph 2</span>
              <button className="flex items-center gap-1 hover:text-blue-600 transition-colors">
                View in Document <ExternalLink className="h-3 w-3" />
              </button>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
            <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-3.5 w-3.5 text-blue-600" />
                <span className="text-sm font-medium text-slate-900">Section 11.1</span>
              </div>
              <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                85% Match
              </span>
            </div>
            <div className="p-4">
              <p className="text-sm text-slate-700 leading-relaxed font-serif">
                &quot;The obligations of confidentiality shall survive for a period of <mark className="bg-yellow-200 text-yellow-900 px-1 rounded">five (5) years</mark> from the termination of this Agreement.&quot;
              </p>
            </div>
            <div className="p-2 border-t border-slate-100 bg-slate-50 flex justify-between items-center text-xs text-slate-500">
              <span>Page 8, Paragraph 4</span>
              <button className="flex items-center gap-1 hover:text-blue-600 transition-colors">
                View in Document <ExternalLink className="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-blue-50 border border-blue-100 p-3">
          <div className="flex gap-2">
            <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
            <p className="text-xs text-blue-800 leading-relaxed">
              The AI generated its response based on the evidence shown above. The highlighted terms were semantically matched to your query using hybrid vector search.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
