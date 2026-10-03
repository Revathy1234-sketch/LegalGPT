"use client";

import { AppShell } from "@/src/components/layout/app-shell";
import { useState, useRef, useEffect } from "react";
import { Bot, Search, Send, FileText, Clock, History, Loader2, Plus, MessageSquare } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/src/lib/api/dashboard";
import Link from "next/link";

interface Message {
  role: "user" | "bot";
  text: string;
}

export default function Workspace() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { role: "bot", text: "Hello! I am LegalGPT. Please select a contract from the sidebar or start typing a general legal query below." }
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: stats } = useQuery({
    queryKey: ['dashboard_stats'],
    queryFn: dashboardApi.getStats,
  });

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages(prev => [...prev, { role: "user", text: input }]);
    setInput("");
    setTimeout(() => {
      setMessages(prev => [...prev, { role: "bot", text: "Please navigate to a specific contract in the Contracts page to perform deep analysis, or use the global search." }]);
    }, 1000);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <AppShell>
      <div className="h-[calc(100vh-8rem)] flex bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        {/* Left Panel - History & Context */}
        <div className="w-80 border-r border-slate-200 bg-slate-50 flex flex-col shrink-0">
          <div className="p-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="font-bold text-slate-900 flex items-center gap-2">
              <History className="h-4 w-4 text-blue-600" />
              Saved Conversations
            </h2>
            <button className="p-1.5 text-blue-600 bg-blue-100 hover:bg-blue-200 rounded-md transition-colors">
              <Plus className="h-4 w-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <div className="p-3 bg-white border border-slate-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 font-medium text-sm text-slate-800 mb-1">
                <MessageSquare className="h-3.5 w-3.5 text-slate-400" />
                NDA Analysis Discussion
              </div>
              <div className="text-xs text-slate-500">2 hours ago</div>
            </div>
            <div className="p-3 bg-white border border-slate-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
              <div className="flex items-center gap-2 font-medium text-sm text-slate-800 mb-1">
                <MessageSquare className="h-3.5 w-3.5 text-slate-400" />
                Employment Terms
              </div>
              <div className="text-xs text-slate-500">Yesterday</div>
            </div>
          </div>
          
          <div className="p-4 border-t border-slate-200 bg-white">
            <h3 className="text-xs font-bold text-slate-500 uppercase mb-3">Recent Analysis Context</h3>
            {stats?.recent_contracts.slice(0,2).map(c => (
              <Link href={`/contracts/${c.id}`} key={c.id} className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded-md transition-colors">
                <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                <div className="truncate flex-1">
                  <div className="text-sm font-medium text-slate-700 truncate">{c.name}</div>
                  <div className="text-xs text-slate-400">{c.lastAnalysis}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Right Panel - Active Chat Area */}
        <div className="flex-1 flex flex-col bg-white min-w-0">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-white z-10 shadow-sm">
            <div>
              <h2 className="font-bold text-lg text-slate-900 flex items-center gap-2">
                <Bot className="h-5 w-5 text-blue-600" />
                Ask LegalGPT
              </h2>
              <p className="text-xs text-slate-500">Global AI Workspace</p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl p-4 ${
                  msg.role === "user" 
                    ? "bg-blue-600 text-white rounded-tr-sm" 
                    : "bg-slate-100 text-slate-800 rounded-tl-sm"
                }`}>
                  <p className="text-sm leading-relaxed">{msg.text}</p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 bg-white border-t border-slate-200">
            <div className="max-w-4xl mx-auto flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask a general legal question or select a contract context..."
                className="flex-1 rounded-full border border-slate-300 px-6 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
              <button 
                onClick={handleSend}
                disabled={!input.trim()}
                className="bg-blue-600 text-white p-3 rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
