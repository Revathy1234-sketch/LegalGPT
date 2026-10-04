import { Database, Info, ExternalLink, X, ShieldAlert, Sparkles, Highlighter } from "lucide-react";
import { useEvidence } from "@/src/contexts/evidence-context";

function HighlightedText({ text, highlight }: { text: string; highlight?: string }) {
  if (!highlight || !text.includes(highlight)) {
    return <>{text}</>;
  }
  const parts = text.split(highlight);
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          {part}
          {i < parts.length - 1 && (
            <mark className="bg-amber-200/80 text-slate-900 px-0.5 rounded-[2px]">
              {highlight}
            </mark>
          )}
        </span>
      ))}
    </>
  );
}

function cleanText(str: string | undefined): string {
  if (!str) return "";
  return str.replace(/[\*\|]/g, "");
}

export function EvidencePanel() {
  const { evidence, sourceType, isOpen, setIsOpen } = useEvidence();

  const header = (
    <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
      <div className="flex items-center gap-2">
        <Database className="h-4 w-4 text-slate-700/60" />
        <h2 className="text-sm font-semibold text-slate-900">Evidence Panel</h2>
      </div>
      <button
        onClick={() => setIsOpen(false)}
        aria-label="Close evidence panel"
        className="text-slate-700/40 hover:text-slate-700/80 rounded-md p-1 hover:bg-slate-200/50 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );

  if (!isOpen && evidence.length === 0) {
    // Automatic evidence: panels populate themselves as analyses run.
    return (
      <div className="flex-1 flex flex-col">
        {header}
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-slate-700/40 text-sm">
          <Sparkles className="h-10 w-10 text-slate-200 mb-3" />
          <p className="text-center leading-relaxed">
            Evidence loads automatically from the PDF as soon as an agent finishes analysing this document.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      {header}

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-700/40 uppercase tracking-wider">Current Source</h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-600/90 border border-blue-100">
              {sourceType}
            </span>
          </div>

          {evidence.length === 0 ? (
            <div className="text-sm text-slate-700/60 italic p-4 bg-slate-50 rounded-lg border border-slate-100">
              Loading evidence from the PDF…
            </div>
          ) : (
            evidence.map((item, index) => (
              <div key={item.id || index} className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden flex flex-col">
                <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <ShieldAlert className="h-4 w-4 text-rose-500 shrink-0" />
                    <span className="text-sm font-bold text-slate-900 truncate">{cleanText(item.finding) || "Analysis"}</span>
                  </div>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase shrink-0 ${
                    item.severity?.toLowerCase().includes('high') || item.severity?.toLowerCase().includes('critical') ? 'bg-rose-50 text-rose-700 border-rose-200' :
                    item.severity?.toLowerCase().includes('low') ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {item.severity || "MEDIUM"}
                  </span>
                </div>

                {item.agent && (
                  <div className="px-3 py-1.5 bg-blue-50/60 border-b border-blue-100 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-blue-500" />
                    <span className="text-[11px] font-semibold text-blue-600/90">{item.agent}</span>
                  </div>
                )}

                {item.explanation && (
                  <div className="p-3 bg-slate-50 border-b border-slate-100">
                    <h4 className="text-xs font-bold text-slate-700/60 uppercase mb-1 tracking-wider">Why</h4>
                    <p className="text-sm text-slate-700">{cleanText(item.explanation)}</p>
                  </div>
                )}

                <div className="p-3 flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-slate-700/60 uppercase tracking-wider flex items-center gap-1">
                      <Highlighter className="h-3 w-3" /> Proof from PDF
                    </h4>
                    <span className="text-xs font-medium text-slate-700/60">{item.page}{item.section ? ` · ${item.section}` : ''}</span>
                  </div>
                  <div className="p-3 bg-blue-50/50 rounded border border-blue-100 relative group">
                    <p className="text-sm text-slate-700 font-serif leading-relaxed italic">
                      “<HighlightedText text={cleanText(item.sourceText)} highlight={cleanText(item.highlight)} />”
                    </p>
                    {typeof item.matchScore === 'number' && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="h-1 flex-1 bg-blue-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${Math.min(Math.round(item.matchScore * 100), 100)}%` }}
                          />
                        </div>
                        <span className="text-[10px] font-semibold text-blue-600/90">
                          {Math.min(Math.round(item.matchScore * 100), 100)}% match
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-2 border-t border-slate-100 bg-slate-50 flex justify-end">
                  <button className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-600/90 transition-colors">
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
              Evidence is quoted verbatim from the uploaded PDF. The highlighted passage is the exact text each agent relied on.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
