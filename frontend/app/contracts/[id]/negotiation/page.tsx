"use client";

import { Scale, Copy, CheckCircle2, ChevronRight, Loader2 } from "lucide-react";
import { useState, use, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import { useEvidence } from "@/src/contexts/evidence-context";
import { evidenceFromNegotiation } from "@/src/lib/evidence-mapper";

export default function NegotiationAdvisor({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const evidence = useEvidence();
  const loadedFor = useRef<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['negotiation', resolvedParams.id],
    queryFn: () => analysisApi.negotiation(resolvedParams.id),
  });

  // Automatic evidence for the Negotiation agent.
  useEffect(() => {
    if (!data || loadedFor.current === resolvedParams.id) return;
    loadedFor.current = resolvedParams.id;
    const items = evidenceFromNegotiation(data.negotiation_suggestions as unknown as Array<Record<string, unknown>>);
    if (items.length > 0) {
      evidence.setSourceType("Negotiation Agent");
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, resolvedParams.id]);

  const suggestions = data?.negotiation_suggestions || [];

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Negotiation Advisor</h2>
        <p className="text-slate-700/60 mt-1 font-medium">AI-suggested redlines and alternative wording based on market standards.</p>
      </div>

      <div className="space-y-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-700/60 bg-white rounded-xl border border-slate-200">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
            <p>Generating negotiation suggestions...</p>
          </div>
        ) : isError ? (
          <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
            Failed to load negotiation suggestions.
          </div>
        ) : suggestions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-700/60 bg-white rounded-xl border border-slate-200">
            <p>No specific negotiation suggestions identified.</p>
          </div>
        ) : (
          suggestions.map((suggestion, idx) => {
            const clause = suggestion.clause || suggestion.title || "General Terms";
            const problem = suggestion.problem || suggestion.issue || "Requires review";
            const impact = suggestion.impact || suggestion.business_impact || "Potential risk exposure.";
            const wording = suggestion.wording || suggestion.suggested_redline || "No alternative wording provided.";
            const priority = suggestion.priority || suggestion.risk_level || "Medium";
            const confidence = suggestion.confidence || "90%";
            return (
              <div key={idx} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-100 shadow-sm">
                      <Scale className="h-4 w-4" />
                    </div>
                    <h3 className="font-bold text-slate-900">{clause}</h3>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border shadow-sm ${
                      priority === 'High' ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      {priority} Priority
                    </span>
                    <span className="text-xs font-semibold text-slate-700/60 bg-white px-2 py-1 rounded border border-slate-200">AI Confidence: {confidence}</span>
                  </div>
                </div>

                <div className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-5">
                    <div>
                      <h4 className="text-xs font-bold text-slate-700/40 uppercase tracking-widest">Identified Problem</h4>
                      <p className="text-sm text-slate-900 mt-1.5 font-semibold">{problem}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-700/40 uppercase tracking-widest">Business Impact</h4>
                      <p className="text-sm text-slate-700 mt-1.5 leading-relaxed">{impact}</p>
                    </div>
                  </div>

                  <div className="bg-slate-50/80 rounded-xl border border-slate-200 p-5 relative group">
                    <h4 className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-3 flex items-center gap-1">
                      Suggested Wording <ChevronRight className="h-3 w-3" />
                    </h4>
                    <p className="text-sm text-slate-900/90 leading-relaxed font-serif bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                      {wording}
                    </p>

                    <button
                      onClick={() => handleCopy(wording, idx)}
                      className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 hover:text-blue-600 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {copiedId === idx ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          <span className="text-emerald-600 font-semibold">Copied to clipboard</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4" />
                          Copy Suggested Wording
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
