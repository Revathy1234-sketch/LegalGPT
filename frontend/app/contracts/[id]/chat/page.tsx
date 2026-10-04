"use client";

import { useState, use, useRef, useEffect, useMemo } from "react";
import { Bot, User, Search, Send, Paperclip, Loader2, FileText, ExternalLink, X } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { chatApi, ContractQuestionResponse } from "@/src/lib/api/chat";
import { contractsApi } from "@/src/lib/api/contracts";
import { useEvidence } from "@/src/contexts/evidence-context";
import { formatISTShort } from "@/src/lib/date-utils";
import { evidenceFromChatSources } from "@/src/lib/evidence-mapper";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "bot";
  text: string;
  at?: string;
  response?: ContractQuestionResponse;
}

export default function ContractChat({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [input, setInput] = useState("");
  const [sent, setSent] = useState<Message[]>([]);
  const [showPdf, setShowPdf] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { setEvidence, setSourceType, setIsOpen } = useEvidence();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const { data: contract } = useQuery({
    queryKey: ["contract", resolvedParams.id],
    queryFn: () => contractsApi.getById(resolvedParams.id),
  });

  const { data: historyData } = useQuery({
    queryKey: ["chatHistory", resolvedParams.id],
    queryFn: () => chatApi.getHistory(resolvedParams.id),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  const messages = useMemo<Message[]>(() => {
    const base = (historyData || []).map((msg) => {
      const meta = (msg.metadata ?? {}) as {
        citations?: Array<Record<string, unknown>>;
        sources?: Array<Record<string, unknown>>;
        confidence?: number;
      };
      const raw = meta?.citations?.length ? meta.citations : (meta?.sources || []);
      const sources = raw.map((c) => ({
        parent_id: String(c.parent_id || ""),
        chunk_id: String(c.chunk_id || ""),
        child_text: String(c.content_preview || c.child_text || c.parent_text || ""),
        parent_text: String(c.content_preview || c.parent_text || c.child_text || ""),
        relevance_score: Number(c.relevance_score ?? c.score ?? 0),
      }));
      return {
        role: msg.role === "user" ? ("user" as const) : ("bot" as const),
        text: msg.content,
        at: msg.created_at,
        response: sources.length > 0
          ? ({ answer: msg.content, confidence: meta?.confidence, sources } as unknown as ContractQuestionResponse)
          : undefined,
      };
    });
    return [...base, ...sent];
  }, [historyData, sent]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const askMutation = useMutation({
    mutationFn: (question: string) => chatApi.ask(resolvedParams.id, question),
    onSuccess: (data) => {
      setSent((prev) => [
        ...prev,
        { role: "bot", text: data.answer, response: data, at: new Date().toISOString() },
      ]);
      if (data.sources && data.sources.length > 0) {
        setEvidence(evidenceFromChatSources(data.sources, "Contract Chat · Retrieval"));
        setSourceType("AI Chat Retrieval");
        setIsOpen(true);
      }
    },
    onError: () => {
      setSent((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, I encountered an error. Please ensure the backend is running and your contract has been indexed." },
      ]);
    },
  });

  const handleSend = (q?: string) => {
    const question = (q || input).trim();
    if (!question || askMutation.isPending) return;
    setInput("");
    setSent((prev) => [...prev, { role: "user", text: question, at: new Date().toISOString() }]);
    askMutation.mutate(question);
  };

  const suggestedQuestions = [
    "Summarize this contract.",
    "What are the biggest risks?",
    "Find confidentiality obligations.",
    "What should I negotiate?",
    "Are there compliance concerns?",
    "List all payment terms.",
  ];

  const pdfUrl = contract?.storage_url
    ? `${API_BASE}${contract.storage_url}`
    : null;

  return (
    <div className="flex h-[calc(100vh-180px)] gap-4">
      {/* PDF Viewer Panel */}
      {showPdf && pdfUrl && (
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col min-w-0">
          <div className="p-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-slate-900/90 truncate max-w-[200px]">
                {contract?.file_name || "Contract PDF"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-md text-slate-700/40 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Open in new tab"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
              <button
                onClick={() => setShowPdf(false)}
                className="p-1.5 rounded-md text-slate-700/40 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                title="Hide PDF"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <iframe
            src={`${pdfUrl}#toolbar=1&navpanes=0`}
            className="flex-1 w-full"
            title="Contract PDF"
            onError={() => setShowPdf(false)}
          />
        </div>
      )}

      {/* Chat Panel */}
      <div className="flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ width: showPdf && pdfUrl ? "42%" : "100%", minWidth: 340 }}>
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="font-semibold text-slate-900 text-sm">LegalGPT Copilot</h2>
              <p className="text-[11px] text-slate-700/60">Grounded in: {contract?.file_name || "..."}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!showPdf && pdfUrl && (
              <button
                onClick={() => setShowPdf(true)}
                className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 bg-blue-50 text-blue-600/90 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <FileText className="h-3.5 w-3.5" /> Show PDF
              </button>
            )}
            <span className="text-xs font-medium text-slate-700/60 bg-white px-2 py-1 rounded-md border border-slate-200">
              Contract Analyst
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-700/60 gap-3">
              <div className="h-14 w-14 rounded-full bg-blue-50 border-2 border-blue-100 flex items-center justify-center">
                <Bot className="h-7 w-7 text-blue-500" />
              </div>
              <p className="font-medium text-slate-700">Ask anything about this contract</p>
              <p className="text-xs text-slate-700/40 text-center max-w-[240px]">
                I have read the full PDF and can answer questions grounded in its exact clauses.
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="flex gap-3">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 border shadow-sm ${
                  msg.role === "user" ? "bg-slate-100 border-slate-200" : "bg-blue-100 border-blue-200"
                }`}>
                  {msg.role === "user" ? (
                    <User className="h-4 w-4 text-slate-700/80" />
                  ) : (
                    <Bot className="h-4 w-4 text-blue-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm text-slate-900 font-medium">
                      {msg.role === "user" ? "You" : "LegalGPT"}
                    </p>
                    {msg.at && (
                      <span className="text-[10px] text-slate-700/40 font-medium">{formatISTShort(msg.at)}</span>
                    )}
                    {msg.role === "bot" && msg.response?.confidence && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                        {(msg.response.confidence * 100).toFixed(0)}% Confidence
                      </span>
                    )}
                  </div>
                  <div className={`text-sm text-slate-700 p-4 rounded-xl rounded-tl-none ${
                    msg.role === "user" ? "bg-slate-50 border border-slate-200" : "bg-blue-50/50 border border-blue-100"
                  }`}>
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                    {msg.role === "bot" && msg.response?.sources && msg.response.sources.length > 0 && (
                      <div className="flex items-center gap-2 p-2 bg-white rounded-md border border-slate-200 shadow-sm mt-3">
                        <Search className="h-4 w-4 text-slate-700/40 shrink-0" />
                        <span className="text-xs text-slate-700/80 font-medium">
                          {msg.response.sources.length} PDF passage{msg.response.sources.length !== 1 ? "s" : ""} retrieved
                        </span>
                        <button
                          onClick={() => {
                            setEvidence(evidenceFromChatSources(msg.response!.sources, "Contract Chat · Retrieval"));
                            setSourceType("AI Chat Retrieval");
                            setIsOpen(true);
                          }}
                          className="text-xs font-medium text-blue-600 ml-auto hover:underline hover:text-blue-600/90 transition-colors"
                        >
                          Show Evidence →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}

          {askMutation.isPending && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border border-blue-200 shadow-sm">
                <Bot className="h-4 w-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm text-slate-900 font-medium">LegalGPT</p>
                </div>
                <div className="text-sm text-slate-700 bg-blue-50/50 border border-blue-100 p-4 rounded-xl rounded-tl-none flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span>Reading contract and composing answer…</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested questions */}
        <div className="px-4 pt-3 flex flex-wrap gap-1.5">
          {suggestedQuestions.map((q, i) => (
            <button
              key={i}
              onClick={() => handleSend(q)}
              disabled={askMutation.isPending}
              className="text-xs px-2.5 py-1.5 bg-white border border-slate-200 rounded-full text-slate-700/80 hover:text-blue-600/90 hover:border-blue-300 hover:bg-blue-50 transition-colors shadow-sm disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask a question about this contract…"
              className="w-full pl-4 pr-24 py-3 border border-slate-200/80 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm transition-all"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <button className="p-1.5 text-slate-700/40 hover:text-slate-700/80 transition-colors rounded-md hover:bg-slate-100 outline-none">
                <Paperclip className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || askMutation.isPending}
                className="p-1.5 bg-blue-600 text-white hover:bg-blue-600/90 transition-colors rounded-lg shadow-sm disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
