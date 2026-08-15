"use client";

import { useState, use, useRef, useEffect } from "react";
import { Bot, User, Search, Send, Paperclip, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { chatApi, ContractQuestionResponse } from "@/lib/api/chat";

interface Message {
  role: "user" | "bot";
  text: string;
  response?: ContractQuestionResponse;
}

export default function ContractChat({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const askMutation = useMutation({
    mutationFn: (question: string) => chatApi.ask(resolvedParams.id, question),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.answer, response: data }
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, I encountered an error while processing your question." }
      ]);
    }
  });

  const handleSend = () => {
    if (!input.trim() || askMutation.isPending) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    askMutation.mutate(userMessage);
  };

  const suggestedQuestions = [
    "Summarize this contract.",
    "What are the biggest risks?",
    "Find confidentiality obligations.",
    "What should I negotiate?",
    "Give me alternative wording.",
    "Are there compliance concerns?",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-600" />
          <h2 className="font-semibold text-slate-900">LegalGPT Copilot</h2>
        </div>
        <span className="text-xs font-medium text-slate-500 bg-white px-2 py-1 rounded-md border border-slate-200">
          Agent: Contract Analyst
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Bot className="h-12 w-12 text-slate-300 mb-4" />
            <p>Ask a question about this contract to get started.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className="flex gap-4">
              <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 border shadow-sm ${
                msg.role === 'user' ? 'bg-slate-100 border-slate-200' : 'bg-blue-100 border-blue-200'
              }`}>
                {msg.role === 'user' ? (
                  <User className="h-4 w-4 text-slate-600" />
                ) : (
                  <Bot className="h-4 w-4 text-blue-600" />
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm text-slate-900 font-medium">
                    {msg.role === 'user' ? 'You' : 'LegalGPT'}
                  </p>
                  {msg.role === 'bot' && msg.response?.confidence && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                      {(msg.response.confidence * 100).toFixed(0)}% Confidence
                    </span>
                  )}
                </div>
                <div className={`text-sm text-slate-700 p-4 rounded-lg rounded-tl-none prose prose-sm max-w-none shadow-sm ${
                  msg.role === 'user' ? 'bg-slate-50 border border-slate-200' : 'bg-blue-50/50 border border-blue-100'
                }`}>
                  <p className="mb-3 whitespace-pre-wrap">{msg.text}</p>

                  {msg.role === 'bot' && msg.response?.sources && msg.response.sources.length > 0 && (
                    <div className="flex items-center gap-2 p-2 bg-white rounded-md border border-slate-200 shadow-sm mt-3">
                      <Search className="h-4 w-4 text-slate-400" />
                      <span className="text-xs text-slate-600 font-medium">
                        Based on {msg.response.sources.length} sources
                      </span>
                      <button className="text-xs font-medium text-blue-600 ml-auto hover:underline hover:text-blue-700 transition-colors">Show Evidence Panel</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {askMutation.isPending && (
          <div className="flex gap-4">
            <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border border-blue-200 shadow-sm">
              <Bot className="h-4 w-4 text-blue-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm text-slate-900 font-medium">LegalGPT</p>
              </div>
              <div className="text-sm text-slate-700 bg-blue-50/50 border border-blue-100 p-4 rounded-lg rounded-tl-none flex items-center gap-2 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-slate-200 bg-slate-50">
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestedQuestions.map((q, i) => (
            <button key={i} className="text-xs px-3 py-1.5 bg-white border border-slate-200 rounded-full text-slate-600 hover:text-blue-700 hover:border-blue-300 hover:bg-blue-50 transition-colors shadow-sm outline-none focus:ring-2 focus:ring-blue-500">
              {q}
            </button>
          ))}
        </div>
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question about this contract..."
            className="w-full pl-4 pr-24 py-3 border border-slate-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white shadow-sm transition-all"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <button className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors rounded-md hover:bg-slate-100 outline-none focus:ring-2 focus:ring-slate-300">
              <Paperclip className="h-4 w-4" />
            </button>
            <button
              onClick={handleSend}
              disabled={!input.trim() || askMutation.isPending}
              className="p-1.5 bg-blue-600 text-white hover:bg-blue-700 transition-colors rounded-md shadow-sm outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
