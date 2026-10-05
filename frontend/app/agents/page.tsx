"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles, FileText, List, ShieldCheck, Scale, Network, GitCompare,
  MessageSquare, Loader2, Play, CheckCircle2, XCircle, ChevronDown, BarChart3,
} from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { AppShell } from "@/src/components/layout/app-shell";
import { EvidenceProvider, useEvidence } from "@/src/contexts/evidence-context";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { RiskDistributionChart } from "@/src/components/dashboard/risk-distribution";
import { contractsApi, ContractResponse } from "@/src/lib/api/contracts";
import { analysisApi, RiskMatrixItem, StoredResultsResponse } from "@/src/lib/api/analysis";
import { dashboardApi } from "@/src/lib/api/dashboard";
import { chatApi } from "@/src/lib/api/chat";
import {
  evidenceFromRiskMatrix,
  evidenceFromClauses,
  evidenceFromCompliance,
  evidenceFromNegotiation,
  evidenceFromKnowledgeGraph,
  evidenceFromChatSources,
} from "@/src/lib/evidence-mapper";
import { riskLevel } from "@/src/lib/risk-utils";

type AgentId =
  | "summary" | "clauses" | "risk" | "compliance"
  | "negotiation" | "knowledge_graph" | "chat" | "compare";

interface AgentState {
  status: "idle" | "running" | "done" | "error";
  preview?: string;
  latencyMs?: number;
}

const AGENTS: {
  id: AgentId;
  name: string;
  statusName: string;
  description: string;
  icon: typeof FileText;
  color: string;
}[] = [
  { id: "summary", name: "Executive Summary", statusName: "Summary", description: "Condenses the whole PDF into a board-ready brief.", icon: FileText, color: "text-blue-600 bg-blue-50 border-blue-100" },
  { id: "clauses", name: "Clause Extraction", statusName: "Clauses", description: "Pulls every clause verbatim with confidence scores.", icon: List, color: "text-indigo-600 bg-indigo-50 border-indigo-100" },
  { id: "risk", name: "Risk Analysis", statusName: "Risk", description: "Scores the contract 0–100 and cites each risk in the PDF.", icon: BarChart3, color: "text-rose-600 bg-rose-50 border-rose-100" },
  { id: "compliance", name: "Compliance Agent", statusName: "Compliance", description: "Checks clauses against regulatory frameworks.", icon: ShieldCheck, color: "text-emerald-600 bg-emerald-50 border-emerald-100" },
  { id: "negotiation", name: "Negotiation Agent", statusName: "Negotiation", description: "Proposes redlines with priority and rationale.", icon: Scale, color: "text-amber-600 bg-amber-50 border-amber-100" },
  { id: "knowledge_graph", name: "Knowledge Graph", statusName: "Knowledge Graph", description: "Builds parties, obligations and clause relationships.", icon: Network, color: "text-purple-600 bg-purple-50 border-purple-100" },
  { id: "chat", name: "Contract Chat (RAG)", statusName: "Chat", description: "Answers questions grounded in retrieved PDF passages.", icon: MessageSquare, color: "text-sky-600 bg-sky-50 border-sky-100" },
  { id: "compare", name: "Comparison Agent", statusName: "Comparison", description: "Compares two contracts for gaps and differences.", icon: GitCompare, color: "text-slate-700 dark:text-slate-200/80 bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700" },
];

function AgentsEvidenceWrapper() {
  const { isOpen } = useEvidence();
  if (!isOpen) return null;
  return (
    <div className="w-80 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hidden xl:flex flex-col shrink-0 relative z-10 shadow-xl m-4 rounded-xl overflow-hidden h-[calc(100vh-8rem)] min-h-0 sticky top-4">
      <EvidencePanel />
    </div>
  );
}

type Slice = { name: string; value: number; color: string; findings: never };

function matrixToSlices(matrix: Array<Record<string, unknown>>): Slice[] {
  let h = 0, m = 0, l = 0;
  const hF: unknown[] = [], mF: unknown[] = [], lF: unknown[] = [];
  matrix.forEach((r) => {
    const sev = String(r.severity || r.risk_level || "").toLowerCase();
    const finding = {
      category: r.category, description: r.issue || r.description,
      impact: r.impact, mitigation: r.mitigation,
      evidence: r.clause_reference, page: r.page, section: r.section,
      source_text: r.source_text, severity: r.severity,
    };
    if (sev === "high" || sev === "critical") { h++; hF.push(finding); }
    else if (sev === "medium") { m++; mF.push(finding); }
    else { l++; lF.push(finding); }
  });
  return [
    { name: "High Risk", value: h, color: "#f43f5e", findings: hF as never },
    { name: "Medium Risk", value: m, color: "#f59e0b", findings: mF as never },
    { name: "Low Risk", value: l, color: "#10b981", findings: lF as never },
  ];
}

/** Human-readable card preview built from a STORED agent result (no re-run). */
function previewFromStored(agentId: string, entry: { result: Record<string, unknown> | null }): string | null {
  const r = entry.result;
  if (!r) return null;
  switch (agentId) {
    case "summary": {
      const s = String((r.summary as string) || "").replace(/[\*\|]/g, "");
      return s ? s.slice(0, 180).replace(/\n/g, " ") + "…" : null;
    }
    case "clauses": {
      const n = Array.isArray(r.clauses) ? r.clauses.length : 0;
      return `${n} clauses extracted with source text`;
    }
    case "risk": {
      const score = Number(r.overall_score ?? 0);
      const n = Array.isArray(r.risk_matrix) ? r.risk_matrix.length : 0;
      return `Score ${score}/100 (${riskLevel(score)}) · ${n} findings`;
    }
    case "compliance": {
      const issues = Array.isArray(r.issues) ? r.issues.length : 0;
      return r.compliant ? "Compliant — no blocking issues" : `${issues} compliance gaps found`;
    }
    case "negotiation": {
      const n = Array.isArray(r.negotiation_suggestions) ? r.negotiation_suggestions.length : 0;
      return `${n} redline suggestions ready`;
    }
    case "knowledge_graph": {
      const inner = (r.result || r) as Record<string, unknown>;
      const ents = Array.isArray(inner.entities) ? inner.entities.length : 0;
      const rels = Array.isArray(inner.relationships) ? inner.relationships.length : 0;
      return `${ents} entities · ${rels} relationships`;
    }
    default:
      return null;
  }
}

/** Evidence items for a STORED agent result — proves without re-running. */
function evidenceFromStored(agentId: string, entry: { result: Record<string, unknown> | null }) {
  const r = entry.result;
  if (!r) return [];
  switch (agentId) {
    case "risk": return evidenceFromRiskMatrix((r.risk_matrix || []) as Array<Record<string, unknown>>);
    case "clauses": return evidenceFromClauses((r.clauses || []) as Array<Record<string, unknown>>);
    case "compliance": return evidenceFromCompliance((r.issues || []) as Array<Record<string, unknown>>);
    case "negotiation": return evidenceFromNegotiation((r.negotiation_suggestions || []) as Array<Record<string, unknown>>);
    case "knowledge_graph": {
      const inner = (r.result || r) as Record<string, unknown>;
      return evidenceFromKnowledgeGraph((inner.entities || []) as Array<Record<string, unknown>>);
    }
    case "summary": {
      const text = String((r.summary as string) || "");
      const bullets = text.split(/\n+/).filter((l) => l.trim().length > 40).slice(0, 6);
      return bullets.map((line, i) => ({
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
    }
    default: return [];
  }
}

function AgentWorkspaceContent() {
  const evidence = useEvidence();
  const router = useRouter();
  // Empty state falls back to the user's contracts (derived, no setState effects).
  const [contractId, setContractId] = useState<string>("");
  const [compareId, setCompareId] = useState<string>("");
  const [states, setStates] = useState<Record<string, { status: "idle" | "running" | "done" | "error"; preview?: string }>>({});

  const { data: contracts, isLoading: loadingContracts } = useQuery({
    queryKey: ["contracts"],
    queryFn: contractsApi.getAll,
  });

  const effectiveContractId = contractId || contracts?.[0]?.id || "";
  const effectiveCompareId = compareId || contracts?.find((c) => c.id !== effectiveContractId)?.id || "";

  // Reset local states and evidence when switching contracts
  useEffect(() => {
    setStates({});
    evidence.setIsOpen(false);
  }, [effectiveContractId, evidence]);

  // STORED agent results — served by GET /analysis/stored/{id} (no LLM calls).
  // This is what makes "run once, view forever" work across page reloads.
  const { data: stored } = useQuery<StoredResultsResponse>({
    queryKey: ["stored_results", effectiveContractId],
    queryFn: () => analysisApi.getStored(effectiveContractId),
    enabled: Boolean(effectiveContractId),
    staleTime: Infinity,
  });

  const setStatus = (id: string, s: { status: "idle" | "running" | "done" | "error"; preview?: string }) => {
    setStates((prev) => {
      const next = { ...prev, [id]: s };
      return next;
    });
  };

  /**
   * Card state = derived from local run state + server-stored results.
   * No effect needed: running/error local states win, otherwise a stored
   * result means "done" (rule 5 — never re-run, just view).
   */
  const stateFor = (id: string): AgentState => {
    const local = states[id];
    if (local?.status === "running" || local?.status === "error") return local;
    // IMPORTANT: Ensure stored results belong to the currently active contract to prevent stale UI during loads.
    const entry = stored?.contract_id === effectiveContractId ? stored?.results?.[id] : undefined;
    if (entry?.has_result) {
      return { status: "done", preview: previewFromStored(id, entry) || local?.preview || "Stored result ready — open to view." };
    }
    return local || { status: "idle" };
  };

  const [riskSlices, setRiskSlices] = useState<Slice[]>([]);
  const prefilledFor = useRef<string | null>(null);

  const { data: agentStatus } = useQuery({
    queryKey: ["agent_status"],
    queryFn: dashboardApi.getAgentStatus,
  });

  // Existing analysis for the selected contract — drives the pre-filled chart.
  const { data: selectedContract } = useQuery({
    queryKey: ["contract", effectiveContractId],
    queryFn: () => contractsApi.getById(effectiveContractId),
    enabled: Boolean(effectiveContractId),
  });

  const prefilledMatrix = useMemo(() => {
    const matrix = (selectedContract?.risk_analysis as { risk_matrix?: Array<Record<string, unknown>> } | undefined)?.risk_matrix;
    return Array.isArray(matrix) && matrix.length > 0 ? matrix : null;
  }, [selectedContract]);

  // Auto-load the PDF proof for an already-analysed contract (runs once per contract).
  useEffect(() => {
    if (!prefilledMatrix || !effectiveContractId || prefilledFor.current === effectiveContractId) return;
    prefilledFor.current = effectiveContractId;
    const items = evidenceFromRiskMatrix(prefilledMatrix);
    if (items.length > 0) {
      evidence.setSourceType("Agent Workspace · Risk Analysis");
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefilledMatrix, effectiveContractId]);


  const showEvidence = (source: string, items: ReturnType<typeof evidenceFromRiskMatrix>) => {
    if (items.length === 0) return;
    evidence.setSourceType(source);
    evidence.setEvidence(items);
    evidence.setIsOpen(true);
  };

  const riskMutation = useMutation({
    mutationFn: (id: string) => analysisApi.risk(id),
    onMutate: () => setStatus("risk", { status: "running" }),
    onSuccess: (data) => {
      const matrix = (data.risk_matrix || []) as RiskMatrixItem[];
      setRiskSlices(matrixToSlices(matrix as unknown as Array<Record<string, unknown>>));
      setStatus("risk", {
        status: "done",
        preview: `Score ${data.overall_score}/100 (${riskLevel(data.overall_score)}) · ${matrix.length} findings`,
      });
      showEvidence("Agent Workspace · Risk Analysis", evidenceFromRiskMatrix(matrix as Array<Record<string, unknown>>));
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Risk analysis failed";
      const isTimeout = msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("network");
      setStatus("risk", { status: "error", preview: isTimeout ? "Timed out — the agent is still processing. Try again in a moment." : msg });
    },
  });

  const clausesMutation = useMutation({
    mutationFn: (id: string) => analysisApi.clauses(id),
    onMutate: () => setStatus("clauses", { status: "running" }),
    onSuccess: (data) => {
      const clauses = (data.clauses || []) as unknown as Array<Record<string, unknown>>;
      setStatus("clauses", { status: "done", preview: `${clauses.length} clauses extracted with source text` });
      showEvidence("Agent Workspace · Clause Extraction", evidenceFromClauses(clauses));
    },
    onError: (err: unknown) =>
      setStatus("clauses", { status: "error", preview: err instanceof Error ? err.message : "Clause extraction failed" }),
  });

  const summaryMutation = useMutation({
    mutationFn: (id: string) => analysisApi.summarize(id),
    onMutate: () => setStatus("summary", { status: "running" }),
    onSuccess: (data) => {
      const text = data.summary || "";
      const bullets = text.split(/\n+/).filter((line) => line.trim().length > 40).slice(0, 6);
      setStatus("summary", { status: "done", preview: text.slice(0, 180).replace(/\n/g, " ") + "…" });
      showEvidence(
        "Agent Workspace · Executive Summary",
        bullets.map((line, i) => ({
          id: `summary-${i}`,
          agent: "Executive Summary",
          finding: line.replace(/^[#>*-\s]+/, "").slice(0, 90),
          severity: "Info",
          explanation: "Condensed by the Summary Agent directly from the uploaded PDF.",
          page: "PDF",
          section: "Summary",
          sourceText: line.slice(0, 500),
          highlight: line.split(/(?<=[.!?])\s/)[0]?.slice(0, 200) || "",
        })),
      );
    },
    onError: (err: unknown) =>
      setStatus("summary", { status: "error", preview: err instanceof Error ? err.message : "Summary failed" }),
  });

  const complianceMutation = useMutation({
    mutationFn: (id: string) => analysisApi.compliance(id),
    onMutate: () => setStatus("compliance", { status: "running" }),
    onSuccess: (data) => {
      const issues = (data.issues || []) as unknown as Array<Record<string, unknown>>;
      setStatus("compliance", {
        status: "done",
        preview: data.compliant ? "Compliant — no blocking issues" : `${issues.length} compliance gaps found`,
      });
      showEvidence("Agent Workspace · Compliance", evidenceFromCompliance(issues));
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Compliance check failed";
      const friendly = msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("network")
        ? "Network timeout — compliance agent takes ~60s. Click Run again."
        : msg;
      setStatus("compliance", { status: "error", preview: friendly });
    },
  });

  const negotiationMutation = useMutation({
    mutationFn: (id: string) => analysisApi.negotiation(id),
    onMutate: () => setStatus("negotiation", { status: "running" }),
    onSuccess: (data) => {
      const suggestions = (data.negotiation_suggestions || []) as unknown as Array<Record<string, unknown>>;
      setStatus("negotiation", { status: "done", preview: `${suggestions.length} redline suggestions ready` });
      showEvidence("Agent Workspace · Negotiation", evidenceFromNegotiation(suggestions));
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Negotiation analysis failed";
      const friendly = msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("network")
        ? "Network timeout — negotiation agent takes ~60s. Click Run again."
        : msg;
      setStatus("negotiation", { status: "error", preview: friendly });
    },
  });


  const kgMutation = useMutation({
    mutationFn: (id: string) => analysisApi.knowledgeGraph(id),
    onMutate: () => setStatus("knowledge_graph", { status: "running" }),
    onSuccess: (data) => {
      const entities = (data.result?.entities || []) as unknown as Array<Record<string, unknown>>;
      const rels = data.result?.relationships?.length || 0;
      setStatus("knowledge_graph", { status: "done", preview: `${entities.length} entities · ${rels} relationships` });
      showEvidence("Agent Workspace · Knowledge Graph", evidenceFromKnowledgeGraph(entities));
    },
    onError: (err: unknown) =>
      setStatus("knowledge_graph", { status: "error", preview: err instanceof Error ? err.message : "Knowledge graph failed" }),
  });

  const chatMutation = useMutation({
    mutationFn: ({ id, question }: { id: string; question: string }) => chatApi.ask(id, question),
    onMutate: () => setStatus("chat", { status: "running" }),
    onSuccess: (data) => {
      setStatus("chat", { status: "done", preview: (data.answer || "").slice(0, 180) + "…" });
      showEvidence("Agent Workspace · Contract Chat", evidenceFromChatSources(data.sources));
    },
    onError: (err: unknown) =>
      setStatus("chat", { status: "error", preview: err instanceof Error ? err.message : "Chat failed" }),
  });

  const compareMutation = useMutation({
    mutationFn: ({ a, b }: { a: string; b: string }) =>
      analysisApi.compare({ contract_a_id: a, contract_b_id: b }),
    onMutate: () => setStatus("compare", { status: "running" }),
    onSuccess: (data) => {
      setStatus("compare", {
        status: "done",
        preview: `${data.similarities.length} similarities · ${data.differences.length} differences · ${data.missing_clauses.length} missing clauses`,
      });
      showEvidence(
        "Agent Workspace · Comparison",
        data.missing_clauses.slice(0, 6).map((clause, i) => ({
          id: `missing-${i}`,
          agent: "Comparison",
          finding: `Missing clause: ${clause}`.slice(0, 90),
          severity: "High",
          explanation: "Present in one contract but absent in the other.",
          page: "PDF",
          section: "Comparison",
          sourceText: clause.slice(0, 400),
          highlight: clause.slice(0, 160),
        })),
      );
    },
    onError: (err: unknown) =>
      setStatus("compare", { status: "error", preview: err instanceof Error ? err.message : "Comparison failed" }),
  });

  const runAgent = (id: AgentId) => {
    if (!effectiveContractId) return;
    // Rule 5: if this agent already has a stored result for this contract,
    // show it instead of re-running (no tokens burned).
    const storedEntry = stored?.results?.[id];
    if (storedEntry?.has_result && storedEntry.result) {
      // User is forcing a re-run from the grid. We will let it run.
    }
    switch (id) {
      case "summary": return summaryMutation.mutate(effectiveContractId);
      case "clauses": return clausesMutation.mutate(effectiveContractId);
      case "risk": return riskMutation.mutate(effectiveContractId);
      case "compliance": return complianceMutation.mutate(effectiveContractId);
      case "negotiation": return negotiationMutation.mutate(effectiveContractId);
      case "knowledge_graph": return kgMutation.mutate(effectiveContractId);
      case "chat": return chatMutation.mutate({ id: effectiveContractId, question: "What are the key obligations and risks in this contract?" });
      case "compare":
        if (!effectiveCompareId || effectiveCompareId === effectiveContractId) return;
        return compareMutation.mutate({ a: effectiveContractId, b: effectiveCompareId });
    }
  };

  const mutations: Partial<Record<AgentId, { isPending: boolean }>> = {
    summary: summaryMutation, clauses: clausesMutation, risk: riskMutation,
    compliance: complianceMutation, negotiation: negotiationMutation,
    knowledge_graph: kgMutation, chat: chatMutation, compare: compareMutation,
  };

  const runAll = () => {
    AGENTS.forEach((agent, i) => {
      if (agent.id === "compare" && (!effectiveCompareId || effectiveCompareId === effectiveContractId)) return;
      // Never re-run agents that already have a stored result (rule 5).
      if (stored?.results?.[agent.id]?.has_result) return;
      window.setTimeout(() => runAgent(agent.id), i * 400);
    });
  };

  const isRunningAny = AGENTS.some((a) => states[a.id]?.status === "running");
  const hasContracts = (contracts?.length || 0) > 0;

  const agentUsage = useMemo(
    () =>
      (agentStatus || [])
        .filter((a) => a.executions > 0)
        .map((a) => ({ name: a.name, count: a.executions })),
    [agentStatus],
  );

  return (
    <div className="flex h-full w-full">
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <Sparkles className="h-7 w-7 text-blue-600" /> Agent Workspace
            </h1>
            <p className="text-slate-700 dark:text-slate-200/60 mt-1 font-medium">
              Run every agent against a contract — results, charts and PDF proof appear on the right.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <select
                value={effectiveContractId}
                onChange={(e) => setContractId(e.target.value)}
                disabled={loadingContracts || !hasContracts}
                className="appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white/90 text-sm rounded-lg pl-9 pr-9 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer font-medium shadow-sm disabled:opacity-60"
              >
                {!hasContracts ? <option>No contracts yet</option> :
                  contracts!.map((c: ContractResponse) => (
                    <option key={c.id} value={c.id}>{c.file_name}</option>
                  ))}
              </select>
              <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700 dark:text-slate-200/40 pointer-events-none" />
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700 dark:text-slate-200/40 pointer-events-none" />
            </div>
            <button
              onClick={runAll}
              disabled={!hasContracts || isRunningAny}
              className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
            >
              {isRunningAny ? "Running agents…" : "Run all agents"}
            </button>
          </div>
        </div>

        {!hasContracts && !loadingContracts && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-200 dark:border-slate-700/80 p-8 text-center text-slate-700 dark:text-slate-200/60">
            <FileText className="h-9 w-9 mx-auto text-slate-300 mb-2" />
            <p className="font-medium text-slate-700 dark:text-slate-200">Upload a contract to activate the agents</p>
            <Link href="/contracts/upload" className="text-sm text-blue-600 hover:underline">Upload a contract →</Link>
          </div>
        )}

        {/* Agent cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {AGENTS.map((agent) => {
            const state = stateFor(agent.id);
            const running = mutations[agent.id]?.isPending || state.status === "running";
            const disabled = !hasContracts || (agent.id === "compare" && (!effectiveCompareId || effectiveCompareId === effectiveContractId));
            return (
              <div
                key={agent.id}
                onClick={() => {
                  if (state.status === "done") {
                    // Show this agent's stored evidence proof inline first…
                    const storedEntry = stored?.contract_id === effectiveContractId ? stored?.results?.[agent.id] : undefined;
                    if (storedEntry?.has_result && storedEntry.result) {
                      const items = evidenceFromStored(agent.id, storedEntry);
                      if (items.length > 0) {
                        evidence.setSourceType(`Agent Workspace · ${agent.name}`);
                        evidence.setEvidence(items);
                        evidence.setIsOpen(true);
                      }
                    }
                    router.push(`/agents/${agent.id}?contractId=${effectiveContractId}`);
                  }
                }}
                className={`bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm flex flex-col gap-3 hover:shadow-md transition-all hover:border-slate-300 dark:hover:border-slate-500 group ${state.status === "done" ? "cursor-pointer" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2.5 rounded-lg border shrink-0 ${agent.color}`}>
                      <agent.icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-slate-900 dark:text-white truncate">{agent.name}</h3>
                      <p className="text-xs text-slate-700 dark:text-slate-200/60 leading-snug mt-0.5">{agent.description}</p>
                    </div>
                  </div>
                  {state.status === "done" && <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />}
                  {state.status === "error" && <XCircle className="h-5 w-5 text-rose-500 shrink-0" />}
                </div>

                <div className="min-h-[38px] rounded-md bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800 px-3 py-2 text-xs text-slate-700 dark:text-slate-200/80 leading-snug">
                  {running ? (
                    <span className="flex items-center gap-1.5 text-blue-600 font-medium">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running…
                    </span>
                  ) : state.status === "error" ? (
                    <span className="text-rose-600">{state.preview || "Failed"}</span>
                  ) : state.status === "done" ? (
                    state.preview
                  ) : (
                    <span className="text-slate-700 dark:text-slate-200/40">Not run yet — evidence will appear here after running.</span>
                  )}
                </div>

                <div className="flex items-center justify-between gap-2 mt-auto">
                  <span className="text-[11px] font-medium text-slate-700 dark:text-slate-200/40">
                    {agentStatus?.find((s) => s.name === agent.statusName)?.executions ?? 0} executions logged
                  </span>
                  <div className="flex items-center gap-2">
                    {state.status === "done" && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            // Toggle behaviour (rules 4 & 10): reopen this
                            // agent's proof, or hide the panel entirely.
                            if (evidence.isOpen) {
                              evidence.setIsOpen(false);
                            } else {
                              const storedEntry = stored?.contract_id === effectiveContractId ? stored?.results?.[agent.id] : undefined;
                              if (storedEntry?.has_result && storedEntry.result) {
                                const items = evidenceFromStored(agent.id, storedEntry);
                                if (items.length > 0) {
                                  evidence.setSourceType(`Agent Workspace · ${agent.name}`);
                                  evidence.setEvidence(items);
                                }
                              }
                              evidence.setIsOpen(true);
                            }
                          }}
                          className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                        >
                          {evidence.isOpen ? "Hide proof" : "Evidence"}
                        </button>
                        <Link
                          href={`/agents/${agent.id}?contractId=${effectiveContractId}`}
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-md border border-emerald-200 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                        >
                          Results →
                        </Link>
                      </>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); runAgent(agent.id); }}
                      disabled={disabled || running}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border border-blue-200 text-blue-600/90 bg-blue-50 hover:bg-blue-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed outline-none focus:ring-2 focus:ring-blue-400"
                    >
                      <Play className="h-3.5 w-3.5" /> {state.status === "done" ? "Re-run" : "Run"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Compare target selector */}
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-700 dark:text-slate-200/60">
          <span>Comparison target:</span>
          <div className="relative">
            <select
              value={effectiveCompareId}
              onChange={(e) => setCompareId(e.target.value)}
              disabled={!hasContracts}
              className="appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm rounded-lg pl-3 pr-8 py-2 outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              {!hasContracts ? <option>—</option> :
                contracts!.map((c: ContractResponse) => (
                  <option key={c.id} value={c.id}>{c.file_name}</option>
                ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-700 dark:text-slate-200/40 pointer-events-none" />
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RiskDistributionChart
            data={riskSlices.length > 0 ? riskSlices : prefilledMatrix ? matrixToSlices(prefilledMatrix) : []}
            title="Risk Distribution"
            subtitle="Auto-populated when the Risk Analysis agent runs — click a slice for proof."
            height={360}
          />
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 sm:p-6 shadow-sm flex flex-col" style={{ height: 360 }}>
            <div className="mb-3 shrink-0">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Agent Executions</h2>
              <p className="text-sm text-slate-700 dark:text-slate-200/60 mt-1">Total runs logged per agent across all contracts.</p>
            </div>
            {agentUsage.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-700 dark:text-slate-200/40 text-sm text-center gap-2">
                <div className="h-14 w-14 rounded-lg border-4 border-dashed border-slate-200 dark:border-slate-700" />
                <p>No agent executions logged yet — run an agent above.</p>
              </div>
            ) : (
              <div className="flex-1 w-full min-h-0">
                <AgentUsageChart data={agentUsage} />
              </div>
            )}
          </div>
        </div>
      </div>

      <AgentsEvidenceWrapper />
    </div>
  );
}

function AgentUsageChart({ data }: { data: { name: string; count: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} interval={0} angle={-18} textAnchor="end" height={55} />
        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
        <Tooltip cursor={{ fill: "#f8fafc" }} contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
        <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function AgentWorkspacePage() {
  return (
    <EvidenceProvider>
      <AppShell>
        <AgentWorkspaceContent />
      </AppShell>
    </EvidenceProvider>
  );
}
