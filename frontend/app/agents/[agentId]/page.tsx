"use client";

import { useEffect, useState, useRef } from "react";
import { use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  ArrowLeft, Play, Loader2, CheckCircle2, XCircle, Network,
  FileText, BarChart3, ShieldCheck, Scale, GitCompare, MessageSquare,
  Sparkles, RefreshCw, Clock, AlertCircle, ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { contractsApi } from "@/src/lib/api/contracts";
import { analysisApi, StoredResultsResponse } from "@/src/lib/api/analysis";
import { chatApi } from "@/src/lib/api/chat";
import {
  evidenceFromRiskMatrix,
  evidenceFromClauses,
  evidenceFromCompliance,
  evidenceFromNegotiation,
  evidenceFromKnowledgeGraph,
  evidenceFromChatSources,
} from "@/src/lib/evidence-mapper";
import { AppShell } from "@/src/components/layout/app-shell";
import { EvidenceProvider, useEvidence } from "@/src/contexts/evidence-context";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { KnowledgeGraphViewer } from "@/src/components/knowledge-graph/knowledge-graph-viewer";

const AGENT_META: Record<string, {
  name: string; description: string; color: string; icon: typeof FileText; badge: string;
}> = {
  summary: {
    name: "Executive Summary", description: "Condenses the whole PDF into a board-ready brief.",
    color: "blue", icon: FileText, badge: "Summary",
  },
  clauses: {
    name: "Clause Extraction", description: "Pulls every clause verbatim with confidence scores.",
    color: "indigo", icon: FileText, badge: "Clauses",
  },
  risk: {
    name: "Risk Analysis", description: "Scores the contract 0–100 and cites each risk in the PDF.",
    color: "rose", icon: BarChart3, badge: "Risk",
  },
  compliance: {
    name: "Compliance Agent", description: "Checks clauses against regulatory frameworks.",
    color: "emerald", icon: ShieldCheck, badge: "Compliance",
  },
  negotiation: {
    name: "Negotiation Agent", description: "Proposes redlines with priority and rationale.",
    color: "amber", icon: Scale, badge: "Negotiation",
  },
  knowledge_graph: {
    name: "Knowledge Graph", description: "Builds parties, obligations and clause relationships.",
    color: "purple", icon: Network, badge: "Knowledge Graph",
  },
  chat: {
    name: "Contract Chat (RAG)", description: "Answers questions grounded in retrieved PDF passages.",
    color: "sky", icon: MessageSquare, badge: "Chat",
  },
  compare: {
    name: "Comparison Agent", description: "Compares two contracts for gaps and differences.",
    color: "slate", icon: GitCompare, badge: "Comparison",
  },
};

function colorCls(color: string, variant: "bg" | "text" | "border" | "badge") {
  const map: Record<string, Record<string, string>> = {
    blue:    { bg: "bg-blue-50",    text: "text-blue-600/90",    border: "border-blue-200",    badge: "bg-blue-100 text-blue-600/90 border-blue-200" },
    indigo:  { bg: "bg-indigo-50",  text: "text-indigo-700",  border: "border-indigo-200",  badge: "bg-indigo-100 text-indigo-700 border-indigo-200" },
    rose:    { bg: "bg-rose-50",    text: "text-rose-700",    border: "border-rose-200",    badge: "bg-rose-100 text-rose-700 border-rose-200" },
    emerald: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", badge: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    amber:   { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",   badge: "bg-amber-100 text-amber-700 border-amber-200" },
    purple:  { bg: "bg-purple-50",  text: "text-purple-700",  border: "border-purple-200",  badge: "bg-purple-100 text-purple-700 border-purple-200" },
    sky:     { bg: "bg-sky-50",     text: "text-sky-700",     border: "border-sky-200",     badge: "bg-sky-100 text-sky-700 border-sky-200" },
    slate:   { bg: "bg-slate-50",   text: "text-slate-700",   border: "border-slate-200",   badge: "bg-slate-100 text-slate-700 border-slate-200" },
  };
  return map[color]?.[variant] || "";
}

function cleanText(str: string): string {
  if (!str) return "";
  return str.replace(/[\*\|]/g, "");
}

type AgentResult =
  | { type: "summary"; data: { summary?: string; [k: string]: unknown } }
  | { type: "clauses"; data: { clauses?: Array<Record<string, unknown>> } }
  | { type: "risk"; data: { overall_score?: number; risk_matrix?: Array<Record<string, unknown>>; mitigation_plan?: string } }
  | { type: "compliance"; data: { compliant?: boolean; issues?: Array<Record<string, unknown>>; recommendations?: string[] } }
  | { type: "negotiation"; data: { negotiation_suggestions?: Array<Record<string, unknown>> } }
  | { type: "knowledge_graph"; data: { result?: { entities?: Array<Record<string, unknown>>; relationships?: Array<Record<string, unknown>> } } }
  | { type: "chat"; data: { answer?: string; sources?: Array<Record<string, unknown>> } }
  | { type: "compare"; data: { similarities?: string[]; differences?: string[]; missing_clauses?: string[]; summary?: string } };

function SummaryResult({ data }: { data: { summary?: string; [k: string]: unknown } }) {
  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
        <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4" /> Executive Summary
        </h3>
        <p className="text-slate-700 whitespace-pre-wrap leading-relaxed text-sm">
          {cleanText(data.summary || "No summary generated.")}
        </p>
      </div>
    </div>
  );
}

function ClausesResult({ data }: { data: { clauses?: Array<Record<string, unknown>> } }) {
  const clauses = data.clauses || [];
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-slate-700/80 font-medium">
        <FileText className="h-4 w-4 text-indigo-600" />
        {clauses.length} clause{clauses.length !== 1 ? "s" : ""} extracted
      </div>
      {clauses.map((c, i) => (
        <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between gap-3 mb-2">
            <h4 className="font-semibold text-slate-900 text-sm">{String(c.title || `Clause ${i + 1}`)}</h4>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 font-medium">
                {String(c.category || "General")}
              </span>
              {Boolean(c.confidence_score) && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 font-medium">
                  {(Number(c.confidence_score) * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
          </div>
          <p className="text-sm text-slate-700/80 leading-relaxed">{String(c.content || "No content.")}</p>
        </div>
      ))}
    </div>
  );
}

function RiskResult({ data }: { data: { overall_score?: number; risk_matrix?: Array<Record<string, unknown>>; mitigation_plan?: string } }) {
  const matrix = data.risk_matrix || [];
  const score = data.overall_score || 0;
  const color = score >= 70 ? "rose" : score >= 40 ? "amber" : "emerald";
  const label = score >= 70 ? "High Risk" : score >= 40 ? "Medium Risk" : "Low Risk";

  return (
    <div className="space-y-4">
      <div className={`rounded-xl p-5 border ${colorCls(color, "bg")} ${colorCls(color, "border")}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-700/80">Overall Risk Score</p>
            <div className="flex items-end gap-2 mt-1">
              <span className={`text-4xl font-bold ${colorCls(color, "text")}`}>{score}</span>
              <span className="text-slate-700/60 text-sm mb-1">/100</span>
            </div>
          </div>
          <span className={`text-sm font-semibold px-3 py-1.5 rounded-lg border ${colorCls(color, "badge")}`}>
            {label}
          </span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-white/60">
          <div
            className={`h-2 rounded-full transition-all duration-700 ${color === "rose" ? "bg-rose-500" : color === "amber" ? "bg-amber-500" : "bg-emerald-500"}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>

      {matrix.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-slate-900/90 text-sm">Risk Findings ({matrix.length})</h3>
          {matrix.map((r, i) => {
            const sev = String(r.severity || r.risk_level || "Medium").toLowerCase();
            const sevColor = sev.includes("high") || sev.includes("critical") ? "rose" : sev.includes("low") ? "emerald" : "amber";
            return (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h4 className="font-semibold text-slate-900 text-sm">{String(r.category || r.title || `Finding ${i + 1}`)}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${colorCls(sevColor, "badge")}`}>
                    {String(r.severity || r.risk_level || "Medium")}
                  </span>
                </div>
                <p className="text-sm text-slate-700/80 mb-2">{String(r.issue || r.description || "")}</p>
                {Boolean(r.mitigation) && (
                  <div className="text-xs text-slate-700/60 bg-slate-50 rounded-lg p-2 border border-slate-100">
                    <span className="font-medium text-slate-700">Mitigation: </span>{String(r.mitigation)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {data.mitigation_plan && (
        <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
          <h3 className="font-semibold text-emerald-900 mb-2 text-sm">Mitigation Plan</h3>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{data.mitigation_plan}</p>
        </div>
      )}
    </div>
  );
}

function ComplianceResult({ data }: { data: { compliant?: boolean; issues?: Array<Record<string, unknown>>; recommendations?: string[] } }) {
  const issues = data.issues || [];
  const recs = data.recommendations || [];
  return (
    <div className="space-y-4">
      <div className={`rounded-xl p-4 border flex items-center gap-3 ${data.compliant ? "bg-emerald-50 border-emerald-200" : "bg-rose-50 border-rose-200"}`}>
        {data.compliant ? (
          <CheckCircle2 className="h-6 w-6 text-emerald-600 shrink-0" />
        ) : (
          <XCircle className="h-6 w-6 text-rose-600 shrink-0" />
        )}
        <div>
          <p className="font-semibold text-slate-900">{data.compliant ? "Compliant" : "Compliance Issues Found"}</p>
          <p className="text-sm text-slate-700/80">{issues.length} issue{issues.length !== 1 ? "s" : ""} identified</p>
        </div>
      </div>

      {issues.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-slate-900/90 text-sm">Issues ({issues.length})</h3>
          {issues.map((iss, i) => {
            const status = String(iss.status || iss.compliance_status || "").toLowerCase();
            const statusColor = status.includes("non") || status.includes("fail") ? "rose" : status.includes("partial") ? "amber" : "emerald";
            return (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3 mb-1">
                  <h4 className="font-semibold text-slate-900 text-sm">{cleanText(String(iss.framework || iss.clause_type || iss.issue || iss.finding || `Issue ${i + 1}`))}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${colorCls(statusColor, "badge")}`}>
                    {cleanText(String(iss.status || iss.compliance_status || "Unknown"))}
                  </span>
                </div>
                {Boolean(iss.gap_analysis || iss.description || iss.explanation) && (
                  <p className="text-sm text-slate-700/80">{cleanText(String(iss.gap_analysis || iss.description || iss.explanation))}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {recs.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
          <h3 className="font-semibold text-blue-900 mb-3 text-sm">Recommendations</h3>
          <ul className="space-y-2">
            {recs.map((rec, i) => {
              let text = "";
              if (typeof rec === "string") text = rec;
              else if (rec && typeof rec === "object") {
                const r = rec as any;
                text = r.recommendation || r.description || r.issue || JSON.stringify(r);
              }
              return (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <ChevronRight className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                  {text}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function NegotiationResult({ data }: { data: { negotiation_suggestions?: Array<Record<string, unknown>> } }) {
  const suggestions = data.negotiation_suggestions || [];
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-slate-700/80 font-medium">
        <Scale className="h-4 w-4 text-amber-600" />
        {suggestions.length} redline suggestion{suggestions.length !== 1 ? "s" : ""}
      </div>
      {suggestions.map((s, i) => {
        const priority = String(s.priority || s.risk_level || "Medium").toLowerCase();
        const priColor = priority.includes("high") ? "rose" : priority.includes("low") ? "emerald" : "amber";
        return (
          <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-start justify-between gap-3">
              <h4 className="font-semibold text-slate-900 text-sm">{cleanText(String(s.clause || s.title || s.topic || s.category || s.clause_title || `Suggestion ${i + 1}`))}</h4>
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium shrink-0 ${colorCls(priColor, "badge")}`}>
                {cleanText(String(s.priority || s.risk_level || "Medium"))}
              </span>
            </div>
            {s.problem || s.issue || s.description || s.rationale || s.reason ? (
              <div className="text-xs text-slate-700/60 bg-rose-50 rounded-lg p-2 border border-rose-100">
                <span className="font-medium text-rose-700">Issue: </span>{cleanText(String(s.problem || s.issue || s.description || s.rationale || s.reason))}
              </div>
            ) : null}
            {s.wording || s.suggested_redline || s.recommendation || s.proposed_change || s.recommended_wording ? (
              <div className="text-xs bg-emerald-50 rounded-lg p-2 border border-emerald-100">
                <span className="font-medium text-emerald-700">Suggested wording: </span>
                <span className="text-slate-700">{cleanText(String(s.wording || s.suggested_redline || s.recommendation || s.proposed_change || s.recommended_wording))}</span>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function CompareResult({ data }: { data: { similarities?: string[]; differences?: string[]; missing_clauses?: string[]; summary?: string } }) {
  return (
    <div className="space-y-4">
      {data.summary && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <h3 className="font-semibold text-slate-900/90 mb-2 text-sm">Summary</h3>
          <p className="text-sm text-slate-700">{data.summary}</p>
        </div>
      )}
      {[
        { label: "Similarities", items: data.similarities || [], color: "emerald" },
        { label: "Differences", items: data.differences || [], color: "amber" },
        { label: "Missing Clauses", items: data.missing_clauses || [], color: "rose" },
      ].map(({ label, items, color }) => items.length > 0 && (
        <div key={label} className={`rounded-xl p-4 border ${colorCls(color as "emerald", "bg")} ${colorCls(color as "emerald", "border")}`}>
          <h3 className={`font-semibold mb-3 text-sm ${colorCls(color as "emerald", "text")}`}>
            {label} ({items.length})
          </h3>
          <ul className="space-y-1.5">
            {items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <ChevronRight className={`h-4 w-4 shrink-0 mt-0.5 ${colorCls(color as "emerald", "text")}`} />
                {item}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function AgentResultView({ result }: { result: AgentResult }) {
  if (result.type === "summary") return <SummaryResult data={result.data} />;
  if (result.type === "clauses") return <ClausesResult data={result.data} />;
  if (result.type === "risk") return <RiskResult data={result.data} />;
  if (result.type === "compliance") return <ComplianceResult data={result.data} />;
  if (result.type === "negotiation") return <NegotiationResult data={result.data} />;
  if (result.type === "knowledge_graph") {
    const entities = result.data.result?.entities || [];
    const rels = result.data.result?.relationships || [];
    return <KnowledgeGraphViewer entities={entities} relationships={rels} />;
  }
  if (result.type === "compare") return <CompareResult data={result.data} />;
  if (result.type === "chat") {
    return (
      <div className="bg-sky-50 border border-sky-100 rounded-xl p-5">
        <p className="text-slate-700 whitespace-pre-wrap leading-relaxed text-sm">{String(result.data.answer || "")}</p>
      </div>
    );
  }
  return null;
}

function AgentDetailContent({ agentId }: { agentId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const evidence = useEvidence();
  const meta = AGENT_META[agentId];
  const [contractId, setContractId] = useState(searchParams.get("contractId") || "");
  const [compareId, setCompareId] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const evidencedFor = useRef<string | null>(null);

  const { data: contracts } = useQuery({ queryKey: ["contracts"], queryFn: contractsApi.getAll });

  // Derived selections (no setState-in-effect): first contract until user picks.
  const activeContractId = contractId || contracts?.[0]?.id || "";
  const activeCompareId = compareId || contracts?.find((c) => c.id !== activeContractId)?.id || "";

  // Stored results — GET only, never re-runs the agent (rules 2 & 5).
  const { data: stored } = useQuery<StoredResultsResponse>({
    queryKey: ["stored_results", activeContractId],
    queryFn: () => analysisApi.getStored(activeContractId),
    enabled: Boolean(activeContractId),
    staleTime: Infinity,
  });

  const showStoredEvidence = (type: string, data: Record<string, unknown>) => {
    try {
      let items: ReturnType<typeof evidenceFromRiskMatrix> = [];
      if (type === "risk") items = evidenceFromRiskMatrix((data.risk_matrix || []) as Array<Record<string, unknown>>);
      else if (type === "clauses") items = evidenceFromClauses((data.clauses || []) as Array<Record<string, unknown>>);
      else if (type === "compliance") items = evidenceFromCompliance((data.issues || []) as Array<Record<string, unknown>>);
      else if (type === "negotiation") items = evidenceFromNegotiation((data.negotiation_suggestions || []) as Array<Record<string, unknown>>);
      else if (type === "knowledge_graph") {
        const inner = (data.result || data) as Record<string, unknown>;
        items = evidenceFromKnowledgeGraph((inner.entities || []) as Array<Record<string, unknown>>);
      } else if (type === "summary") {
        const text = String((data.summary as string) || "");
        items = text.split(/\n+/).filter((l) => l.trim().length > 40).slice(0, 6).map((line, i) => ({
          id: `summary-${i}`,
          agent: "Executive Summary",
          finding: line.replace(/^[#>*-\s]+/, "").slice(0, 90),
          severity: "Info",
          explanation: "Condensed by the Summary Agent directly from the uploaded PDF.",
          page: "PDF",
          section: "Summary",
          sourceText: line.slice(0, 500),
          highlight: line.split(/(?<=[.!?])\s/)[0]?.slice(0, 200) || "",
        }));
      } else if (type === "chat") {
        items = evidenceFromChatSources((data.sources || []) as Array<Record<string, unknown>>);
      } else if (type === "compare") {
        items = ((data.missing_clauses || []) as string[]).slice(0, 6).map((clause, i) => ({
          id: `missing-${i}`,
          agent: "Comparison",
          finding: `Missing clause: ${clause}`.slice(0, 90),
          severity: "High",
          explanation: "Present in one contract but absent in the other.",
          page: "PDF",
          section: "Comparison",
          sourceText: String(clause).slice(0, 400),
          highlight: String(clause).slice(0, 160),
        }));
      }
      if (items.length > 0) {
        evidence.setSourceType(`Agent Workspace · ${meta?.name || type}`);
        evidence.setEvidence(items);
        evidence.setIsOpen(true);
      }
    } catch { /* evidence must never block the result view */ }
  };

  // Auto-load this agent's PDF proof when its stored result arrives
  // (evidence context setters only — no local setState in the effect).
  useEffect(() => {
    if (!stored?.results || !agentId || agentId === "compare" || agentId === "chat") return;
    const entry = stored.results[agentId];
    if (entry?.has_result && entry.result && evidencedFor.current !== `${agentId}:${activeContractId}`) {
      evidencedFor.current = `${agentId}:${activeContractId}`;
      showStoredEvidence(agentId, entry.result);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stored, agentId, activeContractId]);

  // Stop the elapsed timer if the page unmounts mid-run.
  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!activeContractId) throw new Error("No contract selected");
      switch (agentId) {
        case "summary": {
          const d = await analysisApi.summarize(activeContractId);
          return { type: "summary", data: d as unknown as Record<string, unknown> };
        }
        case "clauses": {
          const d = await analysisApi.clauses(activeContractId);
          return { type: "clauses", data: d };
        }
        case "risk": {
          const d = await analysisApi.risk(activeContractId);
          return { type: "risk", data: d };
        }
        case "compliance": {
          const d = await analysisApi.compliance(activeContractId);
          return { type: "compliance", data: d };
        }
        case "negotiation": {
          const d = await analysisApi.negotiation(activeContractId);
          return { type: "negotiation", data: d };
        }
        case "knowledge_graph": {
          const d = await analysisApi.knowledgeGraph(activeContractId);
          return { type: "knowledge_graph", data: d };
        }
        case "chat": {
          const d = await chatApi.ask(activeContractId, "What are the key obligations, risks, and parties in this contract?");
          return { type: "chat", data: d };
        }
        case "compare": {
          if (!activeCompareId || activeCompareId === activeContractId) throw new Error("Select a different contract to compare.");
          const d = await analysisApi.compare({ contract_a_id: activeContractId, contract_b_id: activeCompareId });
          return { type: "compare", data: d };
        }
        default:
          throw new Error("Unknown agent");
      }
    },
    onMutate: () => {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    },
    onSuccess: (data) => {
      if (timerRef.current) clearInterval(timerRef.current);
      // Fresh run → surface its proof in the evidence panel automatically.
      const inner = (data as AgentResult | undefined)?.data as Record<string, unknown> | undefined;
      if (inner) showStoredEvidence(agentId, inner);
    },
    onError: () => {
      if (timerRef.current) clearInterval(timerRef.current);
    },
  });

  const contract = contracts?.find((c) => c.id === activeContractId);

  // Derived view state — an explicit run wins, otherwise the stored server
  // result (rules 2 & 5: revisits show previous output, never re-run).
  // IMPORTANT: Ensure stored results belong to the currently active contract to prevent stale UI during loads.
  const storedEntry = agentId !== "compare" && agentId !== "chat" && stored?.contract_id === activeContractId ? stored?.results?.[agentId] : undefined;
  const hasStored = Boolean(storedEntry?.has_result && storedEntry.result);
  const fromStore = !runMutation.isSuccess && hasStored;
  const result: AgentResult | null = runMutation.isSuccess
    ? (runMutation.data as AgentResult)
    : hasStored
      ? ({ type: agentId, data: storedEntry!.result } as AgentResult)
      : null;
  const status: "idle" | "running" | "done" | "error" = runMutation.isPending
    ? "running"
    : runMutation.isError
      ? "error"
      : result
        ? "done"
        : "idle";
  const errorMsg = runMutation.error instanceof Error ? runMutation.error.message : "Agent failed. Check backend logs.";

  // Explicit user-triggered run/refresh only.
  const runExplicitly = () => {
    runMutation.reset();
    runMutation.mutate();
  };

  if (!meta) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-slate-700/60">
        <AlertCircle className="h-10 w-10 mb-3 text-rose-400" />
        <p className="font-semibold">Unknown agent: {agentId}</p>
        <Link href="/agents" className="mt-3 text-blue-600 hover:underline text-sm">← Back to Agent Workspace</Link>
      </div>
    );
  }

  const Icon = meta.icon;

  return (
    <div className="flex h-full w-full">
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full py-1">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/agents")}
          className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-700/60"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className={`p-3 rounded-xl border ${colorCls(meta.color, "bg")} ${colorCls(meta.color, "border")}`}>
          <Icon className={`h-6 w-6 ${colorCls(meta.color, "text")}`} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            {meta.name}
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${colorCls(meta.color, "badge")}`}>
              {meta.badge}
            </span>
          </h1>
          <p className="text-slate-700/60 text-sm mt-0.5">{meta.description}</p>
        </div>
      </div>

      {/* Config bar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-700/40" />
          <label className="text-sm font-medium text-slate-700">Contract:</label>
          <select
            value={activeContractId}
            onChange={(e) => { runMutation.reset(); evidencedFor.current = null; setContractId(e.target.value); }}
            className="appearance-none bg-slate-50 border border-slate-200 text-slate-900/90 text-sm rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500"
          >
            {(contracts || []).map((c) => (
              <option key={c.id} value={c.id}>{c.file_name}</option>
            ))}
          </select>
        </div>
        {agentId === "compare" && (
          <div className="flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-slate-700/40" />
            <label className="text-sm font-medium text-slate-700">Compare with:</label>
            <select
              value={activeCompareId}
              onChange={(e) => { runMutation.reset(); setCompareId(e.target.value); }}
              className="appearance-none bg-slate-50 border border-slate-200 text-slate-900/90 text-sm rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-blue-500"
            >
              {(contracts || []).map((c) => (
                <option key={c.id} value={c.id}>{c.file_name}</option>
              ))}
            </select>
          </div>
        )}
        <button
          onClick={runExplicitly}
          disabled={runMutation.isPending || !contractId}
          className={`ml-auto flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors shadow-sm disabled:opacity-50 ${
            status === "done" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-blue-600 hover:bg-blue-600/90"
          }`}
        >
          {runMutation.isPending ? (
            <><Loader2 className="h-4 w-4 animate-spin" /> Running… ({elapsed}s)</>
          ) : status === "done" ? (
            <><RefreshCw className="h-4 w-4" /> {fromStore ? "Refresh (re-run)" : "Re-run Agent"}</>
          ) : (
            <><Play className="h-4 w-4" /> Run Agent</>
          )}
        </button>
      </div>

      {/* Status bar */}
      {status !== "idle" && (
        <div className={`rounded-xl px-4 py-3 flex items-center gap-3 text-sm font-medium border ${
          status === "running" ? "bg-blue-50 border-blue-200 text-blue-800" :
          status === "done" ? "bg-emerald-50 border-emerald-200 text-emerald-800" :
          "bg-rose-50 border-rose-200 text-rose-800"
        }`}>
          {status === "running" && <Loader2 className="h-4 w-4 animate-spin" />}
          {status === "done" && <CheckCircle2 className="h-4 w-4" />}
          {status === "error" && <XCircle className="h-4 w-4" />}
          {status === "running" && `Running ${meta.name} on "${contract?.file_name || "contract"}"…`}
          {status === "done" && (fromStore
            ? `Previous ${meta.name} result loaded from storage — not re-run ("${contract?.file_name || "contract"}")`
            : `${meta.name} completed successfully on "${contract?.file_name || "contract"}"`)}
          {status === "error" && `Error: ${errorMsg}`}
          {status !== "running" && (
            <span className="ml-auto flex items-center gap-1 text-xs opacity-70">
              <Clock className="h-3 w-3" /> {elapsed}s
            </span>
          )}
        </div>
      )}

      {/* Result */}
      {status === "idle" && !result && (
        <div className="bg-white rounded-xl border border-dashed border-slate-200/80 p-12 text-center">
          <Sparkles className="h-10 w-10 mx-auto text-slate-300 mb-3" />
          <p className="font-semibold text-slate-700">Ready to run</p>
          <p className="text-sm text-slate-700/60 mt-1">Select a contract and click the Run Agent button to see the full output here.</p>
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-slate-900">Agent Output</h2>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${colorCls(meta.color, "badge")}`}>
              {meta.badge}
            </span>
          </div>
          <AgentResultView result={result} />
        </div>
      )}
      </div>
      </div>

      {/* Evidence panel (rules 4 & 10) — proof on the right, toggleable. */}
      {evidence.isOpen && (
        <div className="w-80 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hidden xl:flex flex-col shrink-0 relative z-10 shadow-xl m-4 rounded-xl overflow-hidden h-[calc(100vh-8rem)] min-h-0 sticky top-4">
          <EvidencePanel />
        </div>
      )}
    </div>
  );
}

export default function AgentDetailPage({ params }: { params: Promise<{ agentId: string }> }) {
  const resolvedParams = use(params);
  return (
    <EvidenceProvider>
      <AppShell>
        <AgentDetailContent agentId={resolvedParams.agentId} />
      </AppShell>
    </EvidenceProvider>
  );
}
