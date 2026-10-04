"use client";

import { useEffect, useRef } from "react";
import { FileText, AlertTriangle, ListChecks, Quote, Loader2, BarChart3, Clock, Users, Target, Shield, Calendar, Scale, Activity } from "lucide-react";
import { StatCard } from "@/src/components/dashboard/stat-card";
import { RiskDistributionChart } from "@/src/components/dashboard/risk-distribution";
import { useQuery } from "@tanstack/react-query";
import { analysisApi, StoredResultsResponse } from "@/src/lib/api/analysis";
import { useEvidence } from "@/src/contexts/evidence-context";
import {
  evidenceFromRiskMatrix,
  evidenceFromClauses,
} from "@/src/lib/evidence-mapper";
import { riskLevel, riskBadgeClass } from "@/src/lib/risk-utils";
import { formatIST } from "@/src/lib/date-utils";

interface Props {
  contractId: string;
}

export function ContractOverviewView({ contractId }: Props) {
  const evidence = useEvidence();
  const evidenceLoadedFor = useRef<string | null>(null);

  const { data: storedData, isLoading, isError } = useQuery<StoredResultsResponse>({
    queryKey: ["stored_results", contractId],
    queryFn: () => analysisApi.getStored(contractId),
  });

  const results = storedData?.results || {};
  const riskMatrix = (results.risk?.result?.risk_matrix as Array<Record<string, unknown>>) || [];
  const overallScore = (results.risk?.result?.overall_score as number) || 0;
  const level = riskLevel(overallScore);
  const clauses = (results.clauses?.result?.clauses as Array<Record<string, unknown>>) || [];
  const summaryText = String(results.summary?.result?.summary || "").replace(/[\*\|]/g, "");
  const kgResult = results.knowledge_graph?.result as any;
  const entities = (kgResult?.result?.entities || kgResult?.result?.nodes || []) as Array<Record<string, unknown>>;
  const complianceIssues = (results.compliance?.result?.issues as Array<Record<string, unknown>>) || [];
  
  // Hub Data Extraction
  const parties = entities.filter(e => {
    const t = String((e.data as any)?.type || e.type || "").toLowerCase();
    return t.includes("party") || t.includes("person") || t.includes("organization") || t.includes("company");
  });
  const obligations = entities.filter(e => String((e.data as any)?.type || e.type || "").toLowerCase().includes("obligation"));
  const dates = entities.filter(e => String((e.data as any)?.type || e.type || "").toLowerCase().includes("date") || String((e.data as any)?.type || e.type || "").toLowerCase().includes("term"));
  const commercial = entities.filter(e => String((e.data as any)?.type || e.type || "").toLowerCase().includes("payment") || String((e.data as any)?.type || e.type || "").toLowerCase().includes("commercial"));

  useEffect(() => {
    if (!storedData || evidenceLoadedFor.current === contractId) return;
    evidenceLoadedFor.current = contractId;

    const riskItems = evidenceFromRiskMatrix(riskMatrix, "Risk Analysis");
    const clauseItems = evidenceFromClauses(clauses, "Clause Extraction");
    const items = [...riskItems, ...clauseItems];

    if (items.length > 0) {
      evidence.setSourceType(`Contract Overview · ${storedData.file_name || ""}`.trim());
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
  }, [storedData, contractId, riskMatrix, clauses, evidence]);

  const riskSlices = (() => {
    let h = 0, m = 0, l = 0;
    const hF: unknown[] = [], mF: unknown[] = [], lF: unknown[] = [];
    (riskMatrix || []).forEach((r) => {
      const sev = String(r.severity || r.risk_level || "").toLowerCase();
      const finding = {
        category: r.category || "General",
        description: r.issue || r.description || r.title || "",
        impact: r.impact || r.financial_impact || r.business_impact || "",
        mitigation: r.mitigation || "",
        evidence: r.clause_reference || r.evidence || "",
        page: r.page || "",
        section: r.section || "",
        source_text: r.source_text || "",
        severity: r.severity || r.risk_level || "Medium",
      };
      if (sev === "high" || sev === "critical") { h++; hF.push(finding); }
      else if (sev === "medium" || sev === "moderate") { m++; mF.push(finding); }
      else { l++; lF.push(finding); }
    });
    return [
      { name: "High Risk", value: h, color: "#f43f5e", findings: hF as never },
      { name: "Medium Risk", value: m, color: "#f59e0b", findings: mF as never },
      { name: "Low Risk", value: l, color: "#10b981", findings: lF as never },
    ];
  })();

  const proofCount = riskMatrix.filter((r) => r.source_text).length + clauses.length;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-700 dark:text-slate-200/60">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
        <p>Loading contract hub…</p>
      </div>
    );
  }

  if (isError || !storedData) {
    return (
      <div className="p-4 bg-rose-50 border border-rose-100 rounded-xl text-rose-600">
        Failed to load contract overview. Check that the backend is running and you are signed in.
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header: Identity */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <FileText className="h-6 w-6 text-blue-600 shrink-0" />
            <span className="truncate">{storedData.file_name || "Contract Overview"}</span>
          </h2>
          <p className="text-slate-700 dark:text-slate-200/60 mt-1.5 font-medium text-sm flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-blue-600" />
              Uploaded {storedData.uploaded_at ? formatIST(storedData.uploaded_at) : "Unknown"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-emerald-600" />
              Contract Hub Active
            </span>
          </p>
        </div>
        <div className="flex items-center gap-3">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border ${complianceIssues.length ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
              <Shield className="w-3.5 h-3.5 mr-1" /> Health: {complianceIssues.length ? `${complianceIssues.length} Issues` : 'OK'}
            </span>
            <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold border ${riskBadgeClass(level)}`}>
              {level} Risk · {overallScore}/100
            </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Clauses"
          value={clauses.length}
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          title="Risk Findings"
          value={riskMatrix.length}
          icon={<AlertTriangle className="h-5 w-5" />}
        />
        <StatCard
          title="Extracted Entities"
          value={entities.length}
          icon={<BarChart3 className="h-5 w-5" />}
        />
        <StatCard
          title="Proof Points"
          value={proofCount}
          icon={<Quote className="h-5 w-5" />}
        />
      </div>

      {/* Purpose & Scope (Summary) */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Purpose & Scope (Executive Summary)</h3>
        </div>
        <div className="prose prose-sm prose-slate max-w-none text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
          {summaryText && summaryText !== "{}" ? summaryText : "No summary available yet. Run the Summary Agent in the workspace."}
        </div>
      </div>

      {/* Hub Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        
        {/* Parties */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-indigo-500" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Parties</h3>
            </div>
            <span className="text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-full">{parties.length}</span>
          </div>
          <div className="flex-1 space-y-2">
            {!parties.length ? <p className="text-sm text-slate-500 italic">Run Knowledge Graph to extract.</p> : 
              parties.slice(0, 5).map((p, i) => (
                <div key={i} className="p-2 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300">
                  {String((p.data as any)?.label || p.label || "Unknown Party")}
                </div>
              ))
            }
          </div>
        </div>

        {/* Dates */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-emerald-500" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Important Dates</h3>
            </div>
            <span className="text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-full">{dates.length}</span>
          </div>
          <div className="flex-1 space-y-2">
            {!dates.length ? <p className="text-sm text-slate-500 italic">Run Knowledge Graph to extract.</p> : 
              dates.slice(0, 5).map((d, i) => (
                <div key={i} className="p-2 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 flex justify-between">
                  <span>{String((d.data as any)?.label || d.label || "Date")}</span>
                </div>
              ))
            }
          </div>
        </div>

        {/* Obligations */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-amber-500" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Key Obligations</h3>
            </div>
            <span className="text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 px-2 py-1 rounded-full">{obligations.length}</span>
          </div>
          <div className="flex-1 space-y-2">
            {!obligations.length ? <p className="text-sm text-slate-500 italic">Run Knowledge Graph to extract.</p> : 
              obligations.slice(0, 5).map((o, i) => (
                <div key={i} className="p-2 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm text-slate-700 dark:text-slate-300 line-clamp-2">
                  {String((o.data as any)?.label || o.label || "Obligation")}
                </div>
              ))
            }
          </div>
        </div>

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Important Clauses */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-indigo-500" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Clauses Overview</h3>
            </div>
            <span className="text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-full">
              {clauses.length} extracted
            </span>
          </div>
          <div className="flex-1 space-y-3">
            {!clauses.length ? (
              <p className="text-sm text-slate-700 dark:text-slate-200/60 italic">Run Clauses agent to extract.</p>
            ) : (
              clauses.slice(0, 4).map((c, i) => (
                <div key={i} className="p-3 bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex justify-between gap-2 mb-1">
                    <span className="font-semibold text-sm text-slate-900 dark:text-white">{String(c.title || c.category || `Clause ${i+1}`)}</span>
                    <span className="text-xs text-slate-700 dark:text-slate-200">{String(c.category || "General")}</span>
                  </div>
                  <p className="text-xs text-slate-700 dark:text-slate-200 line-clamp-2">{String(c.content || c.original_text || "No content")}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Attention Areas / High Risk Findings */}
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-rose-500" />
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Attention Areas (Risks)</h3>
            </div>
          </div>
          <div className="flex-1 space-y-3">
            {(() => {
              const highRisks = (riskMatrix || []).filter((r) => {
                const s = String(r.severity || r.risk_level || "").toLowerCase();
                return s === "high" || s === "critical";
              });
              
              if (highRisks.length === 0) {
                return <p className="text-sm text-slate-700 dark:text-slate-200/60 italic">No high-risk findings detected.</p>;
              }
              
              return highRisks.slice(0, 4).map((r, i) => (
                <div key={i} className="p-3 bg-rose-50/50 border border-rose-100 rounded-lg">
                  <span className="font-semibold text-sm text-rose-900">{String(r.category || r.title || "Risk Finding")}</span>
                  <p className="text-xs text-rose-700/80 mt-1 line-clamp-2">{String(r.issue || r.description || "")}</p>
                </div>
              ));
            })()}
          </div>
        </div>
      </div>

      {/* Risk Distribution */}
      <RiskDistributionChart data={riskSlices} height={380} />
    </div>
  );
}
