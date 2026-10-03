"use client";

import { use } from "react";
import { AlertTriangle, ShieldAlert, Info, Loader2, CheckCircle2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api/analysis";
import { useEvidence, EvidenceItem } from "@/src/contexts/evidence-context";

export default function RiskAnalysis({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['risk', resolvedParams.id],
    queryFn: () => analysisApi.risk(resolvedParams.id),
  });

  const { setEvidence, setSourceType, setIsOpen } = useEvidence();

  const risks = data?.risk_matrix || [];
  const overallScore = data?.overall_score || 0;
  const isHighRisk = overallScore < -1;
  const isMediumRisk = overallScore >= -1 && overallScore < 0;

  return (
    <div className="space-y-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Risk Analysis</h2>
          <p className="text-slate-500 mt-1 font-medium">AI-driven identification of potential liabilities and exposures.</p>
        </div>
        {!isLoading && !isError && (
          <div className={`px-3 py-2 rounded-lg border flex items-center gap-2 shadow-sm ${
            isHighRisk ? 'bg-rose-50 border-rose-200' : isMediumRisk ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'
          }`}>
            {isHighRisk ? <ShieldAlert className="h-4 w-4 text-rose-600" /> : isMediumRisk ? <AlertTriangle className="h-4 w-4 text-amber-600" /> : <Info className="h-4 w-4 text-emerald-600" />}
            <span className={`text-sm font-semibold ${
              isHighRisk ? 'text-rose-800' : isMediumRisk ? 'text-amber-800' : 'text-emerald-800'
            }`}>
              Overall Risk: {isHighRisk ? 'High' : isMediumRisk ? 'Medium' : 'Low'}
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="bg-blue-50/80 rounded-xl border border-blue-100 p-6 flex flex-col justify-center">
          <div className="flex gap-4">
            <Info className="h-6 w-6 text-blue-600 shrink-0" />
            <div>
              <h3 className="font-bold text-blue-900">Important Disclaimer</h3>
              <p className="text-sm text-blue-800 mt-2 leading-relaxed font-medium">
                AI-generated analysis should be reviewed by qualified professionals. LegalGPT does not provide legal advice, and its risk assessments are based on semantic analysis against standard market practices.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4 pt-2">
        <h3 className="text-lg font-bold text-slate-900">Identified Risk Factors</h3>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
            <p>Analyzing risk factors...</p>
          </div>
        ) : isError ? (
          <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
            Failed to load risk analysis.
          </div>
        ) : risks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
            <p>No significant risks identified.</p>
          </div>
        ) : (
          risks.map((risk, idx) => {
            const severity = risk.severity || risk.risk_level || ((risk.overall_score ?? 0) < -1 ? 'High' : (risk.overall_score ?? 0) < 0 ? 'Medium' : 'Low');
            return (
              <div 
                key={idx} 
                className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col sm:flex-row cursor-pointer hover:border-blue-300 transition-colors"
                onClick={() => {
                  const ev: EvidenceItem = {
                    id: String(idx),
                    section: String(risk.issue || risk.title || "Risk Finding"),
                    text: risk.evidence ? String(risk.evidence) : "Specific contract text not extracted. The model flagged this risk based on the section referenced.",
                    page: (risk.source || risk.page) ? String(risk.source || risk.page) : "Contract"
                  };
                  setEvidence([ev]);
                  setSourceType("Risk Analysis Agent");
                  setIsOpen(true);
                }}
              >
                <div className={`p-5 sm:w-56 shrink-0 flex flex-col justify-center border-b sm:border-b-0 sm:border-r border-slate-100 ${
                  severity === 'High' ? 'bg-rose-50/50' : severity === 'Medium' ? 'bg-amber-50/50' : 'bg-emerald-50/50'
                }`}>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border w-max shadow-sm ${
                    severity === 'High' ? 'bg-rose-100 text-rose-700 border-rose-200' : severity === 'Medium' ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-emerald-100 text-emerald-700 border-emerald-200'
                  }`}>
                    {severity === 'High' ? <ShieldAlert className="h-3.5 w-3.5" /> : severity === 'Medium' ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    {severity} Risk
                  </span>
                  <span className="text-xs text-slate-500 mt-4 font-medium">Source: <button className="text-blue-600 hover:underline font-semibold">{risk.source || 'General'}</button></span>
                </div>
                <div className="p-5 sm:p-6 space-y-4 flex-1">
                  <div>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Issue</h4>
                    <p className="text-sm text-slate-900 mt-1 font-semibold">{risk.issue || risk.description || risk.title}</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-slate-100">
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Business Impact</h4>
                      <p className="text-sm text-slate-700 mt-1.5 leading-relaxed font-serif">{risk.impact || risk.business_impact || "Potential financial or operational liability."}</p>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Suggested Mitigation</h4>
                      <p className="text-sm text-slate-700 mt-1.5 leading-relaxed font-serif">{risk.mitigation || risk.suggestion || "Review and negotiate terms."}</p>
                    </div>
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
