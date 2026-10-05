"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import {
  Bot, Send, FileText, History, Loader2, Plus, MessageSquare,
  Sparkles, ExternalLink, ChevronDown,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { dashboardApi } from "@/src/lib/api/dashboard";
import { chatApi, WorkspaceMessage } from "@/src/lib/api/chat";
import { contractsApi, ContractResponse } from "@/src/lib/api/contracts";
import { AppShell } from "@/src/components/layout/app-shell";
import { EvidenceProvider, useEvidence } from "@/src/contexts/evidence-context";
import { EvidencePanel } from "@/src/components/contracts/evidence-panel";
import { RiskDistributionChart } from "@/src/components/dashboard/risk-distribution";
import { AgentUsageMini } from "@/src/components/dashboard/agent-usage-mini";
import { evidenceFromChatSources } from "@/src/lib/evidence-mapper";
import { formatISTShort } from "@/src/lib/date-utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "https://legalgpt-backend.fastapicloud.dev" : "http://localhost:8000");

interface Message {
  role: "user" | "bot";
  text: string;
  at?: string;
  error?: boolean;
}

const GREETING: Message = {
  role: "bot",
  text: "Hello! I am LegalGPT — your AI legal assistant. Select a contract from the dropdown to ground my answers in specific PDF passages, or ask general legal questions without selecting one.\n\nTry: \"Summarize the key risks in this contract\" or \"What are the payment obligations?\"",
};

const QUICK_QUESTIONS = [
  "What are the key risks in this contract?",
  "Summarize the main obligations of each party.",
  "Are there any compliance concerns?",
  "What are the payment and termination terms?",
  "Identify any one-sided or unfair clauses.",
];

function WorkspaceEvidenceColumn() {
  const { data: stats } = useQuery({
    queryKey: ["dashboard_stats"],
    queryFn: dashboardApi.getStats,
    retry: 1,
  });
  const evidence = useEvidence();
  const autoLoaded = useRef(false);

  useEffect(() => {
    if (!stats || autoLoaded.current) return;
    autoLoaded.current = true;
    const items = (stats.risk_distribution || [])
      .flatMap((slice) => (slice.findings || []).map((f, i) => ({
        id: `ws-${slice.name}-${i}`,
        agent: "Risk Analysis",
        finding: String(f.description || f.category || "Risk finding").slice(0, 90),
        severity: slice.name,
        explanation: String(f.mitigation || f.impact || "Identified in the uploaded PDF.").slice(0, 300),
        page: f.page || "PDF",
        section: f.section || f.category || "",
        sourceText: String(f.source_text || f.description || "No verbatim passage captured.").slice(0, 500),
        highlight: String(f.source_text || "").split(/(?<=[.!?])\s/)[0]?.slice(0, 200) || "",
      })));
    if (items.length > 0) {
      evidence.setSourceType("Workspace · Risk Findings");
      evidence.setEvidence(items);
      evidence.setIsOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats]);

  return (
    <div className="w-96 border-l border-slate-200 bg-white hidden xl:flex flex-col shrink-0 relative z-10">
      <div className="flex flex-col gap-4 p-4 border-b border-slate-200">
        <div className="grid grid-cols-1 gap-4">
          <RiskDistributionChart
            data={stats?.risk_distribution || []}
            title="Risk Distribution"
            subtitle="Click a slice to inspect the PDF proof."
            height={300}
            statusDistribution={stats?.status_distribution}
            riskRadar={stats?.risk_radar}
            agentUsage={stats?.agent_usage}
          />
          <AgentUsageMini data={stats?.agent_usage || []} />
        </div>
      </div>
      <div className="flex-1 min-h-0 flex flex-col border-t border-slate-200">
        <EvidencePanel />
      </div>
    </div>
  );
}

// Derive a meaningful title from the first message
function deriveTitleFromMessage(message: string): string {
  const clean = message.trim().replace(/[?!.]+$/, "");
  const words = clean.split(/\s+/);
  const title = words.slice(0, 8).join(" ");
  return title.length > 60 ? title.slice(0, 60) + "…" : title;
}

function WorkspaceContent() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [contractContext, setContractContext] = useState<string>("");
  const [showQuick, setShowQuick] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const evidence = useEvidence();

  const { data: sessions, isLoading: loadingSessions } = useQuery({
    queryKey: ["workspace_sessions"],
    queryFn: chatApi.listWorkspaceSessions,
    refetchInterval: 10000,
  });

  const { data: contracts } = useQuery({
    queryKey: ["contracts"],
    queryFn: contractsApi.getAll,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const openSession = async (sessionId: string) => {
    if (sessionId === activeSessionId) return;
    setLoadingHistory(true);
    setActiveSessionId(sessionId);
    const s = sessions?.find((s) => s.id === sessionId);
    setSessionTitle(s?.title || "");
    try {
      const history: WorkspaceMessage[] = await chatApi.getWorkspaceMessages(sessionId);
      setMessages(
        history.length
          ? history.map((m) => ({
              role: m.role === "user" ? ("user" as const) : ("bot" as const),
              text: m.content,
              at: m.created_at,
              error: Boolean((m.metadata as { error?: string } | null)?.error),
            }))
          : [GREETING],
      );
    } catch {
      setMessages([{ role: "bot", text: "Could not load this conversation." }]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const newConversation = () => {
    setActiveSessionId(null);
    setSessionTitle("");
    setMessages([GREETING]);
    setShowQuick(true);
  };

  const handleSend = useCallback(async (overrideQuestion?: string) => {
    const question = (overrideQuestion || input).trim();
    if (!question || sending) return;
    setInput("");
    setSending(true);
    setShowQuick(false);
    setMessages((prev) => [...prev, { role: "user", text: question, at: new Date().toISOString() }]);

    // Derive a title from the first user message if this is a new session
    if (!activeSessionId && !sessionTitle) {
      setSessionTitle(deriveTitleFromMessage(question));
    }

    try {
      const res = await chatApi.workspaceAsk(question, activeSessionId, contractContext || null);
      if (!activeSessionId) setActiveSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: res.answer, at: res.created_at, error: res.error },
      ]);
      queryClient.invalidateQueries({ queryKey: ["workspace_sessions"] });

      const sources = (res as { sources?: Parameters<typeof evidenceFromChatSources>[0] }).sources;
      if (sources && sources.length > 0) {
        const items = evidenceFromChatSources(sources, "Workspace · Contract Chat");
        evidence.setSourceType("Workspace · Contract Chat");
        evidence.setEvidence(items);
        evidence.setIsOpen(true);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "Unable to complete the request. Please try again.",
          at: new Date().toISOString(),
          error: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, activeSessionId, sessionTitle, contractContext, queryClient, evidence]);

  const selectedContract = contracts?.find((c) => c.id === contractContext);

  return (
    <div className="flex h-full w-full">
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 shrink-0">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Sparkles className="h-7 w-7 text-blue-600" />
              AI Workspace
            </h1>
            <p className="text-slate-700/60 mt-1 font-medium text-sm">
              Global legal chat — every prompt and response is saved automatically.
            </p>
          </div>
          <button
            onClick={newConversation}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-600/90 font-medium text-sm transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
          >
            <Plus className="h-4 w-4" /> New conversation
          </button>
        </div>

        <div className="flex-1 min-h-0 flex bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          {/* Saved conversations sidebar */}
          <div className="w-72 border-r border-slate-200 bg-slate-50 flex flex-col shrink-0">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <History className="h-4 w-4 text-blue-600" />
                Saved Conversations
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {loadingSessions ? (
                <div className="flex items-center justify-center py-8 text-slate-700/40">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : !sessions || sessions.length === 0 ? (
                <p className="text-xs text-slate-700/40 text-center py-6 leading-relaxed">
                  No saved conversations yet. Start chatting to see them here.
                </p>
              ) : (
                sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => openSession(s.id)}
                    className={`w-full text-left p-3 bg-white border rounded-xl cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all ${
                      activeSessionId === s.id ? "border-blue-400 ring-1 ring-blue-200 bg-blue-50/50" : "border-slate-200"
                    }`}
                  >
                    <div className="flex items-start gap-2 font-medium text-sm text-slate-900/90 mb-1">
                      <MessageSquare className="h-3.5 w-3.5 text-slate-700/40 shrink-0 mt-0.5" />
                      <span className="truncate leading-tight">{s.title || "Conversation"}</span>
                    </div>
                    <div className="text-xs text-slate-700/60 flex items-center justify-between">
                      <span>{formatISTShort(s.updated_at)}</span>
                      <span className="text-slate-700/40">{s.message_count} msgs</span>
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Contract context selector */}
            <div className="p-4 border-t border-slate-200 bg-white space-y-3">
              <h3 className="text-xs font-bold text-slate-700/60 uppercase">Contract Context</h3>
              <div className="relative">
                <select
                  value={contractContext}
                  onChange={(e) => setContractContext(e.target.value)}
                  className="w-full appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-md pl-8 pr-8 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">General legal questions</option>
                  {(contracts || []).map((c: ContractResponse) => (
                    <option key={c.id} value={c.id}>{c.file_name}</option>
                  ))}
                </select>
                <FileText className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-700/40 pointer-events-none" />
                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-700/40 pointer-events-none" />
              </div>

              {selectedContract && (
                <Link
                  href={`/contracts/${selectedContract.id}/chat`}
                  className="flex items-center justify-between gap-2 p-2.5 bg-blue-50 border border-blue-100 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                    <span className="text-xs font-medium text-blue-600/90 truncate">{selectedContract.file_name}</span>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                </Link>
              )}

              {!selectedContract && (contracts || []).length > 0 && (
                <p className="text-xs text-slate-700/40">
                  Select a contract above to chat with its PDF content.
                </p>
              )}
            </div>
          </div>

          {/* Chat area */}
          <div className="flex-1 flex flex-col bg-white min-w-0">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-white z-10 shadow-sm">
              <div>
                <h2 className="font-bold text-lg text-slate-900 flex items-center gap-2">
                  <Bot className="h-5 w-5 text-blue-600" />
                  {sessionTitle || "Ask LegalGPT"}
                </h2>
                <p className="text-xs text-slate-700/60">
                  {contractContext
                    ? `📎 Grounded in: ${contracts?.find((c) => c.id === contractContext)?.file_name || "selected contract"}`
                    : "Global AI Workspace — no specific contract selected"}
                </p>
              </div>
              {activeSessionId && (
                <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-md">
                  Auto-saving
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {loadingHistory && (
                <div className="flex items-center justify-center py-8 text-slate-700/40 gap-2 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading conversation…
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "bot" && (
                    <div className="h-8 w-8 rounded-full bg-blue-100 border border-blue-200 flex items-center justify-center shrink-0 mr-2 mt-1">
                      <Bot className="h-4 w-4 text-blue-600" />
                    </div>
                  )}
                  <div className={`max-w-[80%] ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm"
                      : msg.error
                        ? "bg-rose-50 text-rose-800 border border-rose-200 rounded-2xl rounded-tl-sm"
                        : "bg-slate-100 text-slate-900/90 rounded-2xl rounded-tl-sm"
                  } p-4`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    {msg.at && (
                      <p className={`text-[10px] mt-2 ${msg.role === "user" ? "text-blue-100" : "text-slate-700/40"}`}>
                        {formatISTShort(msg.at)}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="h-8 w-8 rounded-full bg-blue-100 border border-blue-200 flex items-center justify-center shrink-0 mr-2 mt-1">
                    <Bot className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="bg-slate-100 text-slate-700/60 rounded-2xl rounded-tl-sm p-4 flex items-center gap-2 text-sm">
                    <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick questions */}
            {showQuick && messages.length <= 1 && (
              <div className="px-6 pb-3 flex flex-wrap gap-2">
                {QUICK_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    disabled={sending}
                    className="text-xs px-3 py-1.5 bg-white border border-slate-200 rounded-full text-slate-700/80 hover:text-blue-600/90 hover:border-blue-300 hover:bg-blue-50 transition-colors shadow-sm disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            <div className="p-4 bg-white border-t border-slate-200">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder={contractContext
                    ? `Ask about ${contracts?.find((c) => c.id === contractContext)?.file_name || "the contract"}…`
                    : "Ask a legal question — it will be saved to history…"}
                  className="flex-1 rounded-full border border-slate-200/80 px-6 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || sending}
                  aria-label="Send message"
                  className="bg-blue-600 text-white p-3 rounded-full hover:bg-blue-600/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <WorkspaceEvidenceColumn />
    </div>
  );
}

export default function Workspace() {
  return (
    <EvidenceProvider>
      <AppShell>
        <WorkspaceContent />
      </AppShell>
    </EvidenceProvider>
  );
}
