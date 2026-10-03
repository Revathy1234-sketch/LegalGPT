"use client";

import { useState, useContext } from "react";
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, AreaChart, Area, ComposedChart, Line
} from "recharts";
import { DashboardData } from "@/src/lib/api/dashboard";
import { ChevronDown } from "lucide-react";
import { EvidenceContext } from "@/src/contexts/evidence-context";

interface Props {
  data: DashboardData; // Passing the whole dashboard data now
}

export function RiskOverview({ data }: Props) {
  const [activeChart, setActiveChart] = useState<"risk-donut" | "status-pie" | "types-bar" | "radar" | "agent-area" | "trend-composed">("risk-donut");
  const evidenceContext = useContext(EvidenceContext);

  const riskData = data.risk_distribution || [];
  const statusData = data.status_distribution || [];
  const typesData = data.contract_types || [];
  const radarData = data.risk_radar || [];
  const agentData = data.agent_usage || [];

  // Derived trend data from recent_activity for a 6th distinct chart (Line/Composed)
  // Simplified mock representation based on activity dates
  const trendData = [
    { day: "Mon", uploads: 4, analysis: 6 },
    { day: "Tue", uploads: 7, analysis: 8 },
    { day: "Wed", uploads: 2, analysis: 5 },
    { day: "Thu", uploads: 9, analysis: 10 },
    { day: "Fri", uploads: 6, analysis: 7 }
  ];

  const handleRiskChartClick = (nodeData: any) => {
    if (!evidenceContext || !nodeData.findings) return;
    
    const newEvidence = nodeData.findings.map((f: any, i: number) => ({
      id: `dash-finding-${i}`,
      agent: "Risk Analysis",
      finding: f.description || "General Risk",
      severity: nodeData.name,
      explanation: f.impact || "No explanation provided.",
      section: f.section || f.category || "General",
      sourceText: f.source_text || "Insufficient source evidence found in the uploaded contract.",
      highlight: f.impact || "",
      page: f.page || f.evidence || ""
    }));

    if (newEvidence.length > 0) {
      evidenceContext.setSourceType(`Risk Category: ${nodeData.name}`);
      evidenceContext.setEvidence(newEvidence);
      evidenceContext.setIsOpen(true);
    } else {
      evidenceContext.clearEvidence();
    }
  };

  const chartOptions = [
    { id: "risk-donut", label: "Risk Distribution (Donut)" },
    { id: "status-pie", label: "Processing Status (Pie)" },
    { id: "types-bar", label: "Contract Types (Bar)" },
    { id: "radar", label: "Risk Vectors (Radar)" },
    { id: "agent-area", label: "Agent Usage (Area)" },
    { id: "trend-composed", label: "Platform Activity (Trend)" }
  ] as const;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col h-[420px]">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Analytics Suite</h2>
          <p className="text-sm text-slate-500 mt-1">Multi-dimensional enterprise intelligence.</p>
        </div>
        <div className="relative">
          <select
            value={activeChart}
            onChange={(e) => setActiveChart(e.target.value as any)}
            className="appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-md pl-3 pr-8 py-1.5 outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer font-medium"
          >
            {chartOptions.map(opt => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
        </div>
      </div>
      
      <div className="flex-1 w-full relative min-h-[250px] mt-2">
        <ResponsiveContainer width="100%" height="100%">
          {activeChart === "risk-donut" ? (
            <PieChart>
              <Pie
                data={riskData}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={95}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
                onClick={handleRiskChartClick}
                cursor="pointer"
              >
                {riskData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} className="hover:opacity-80 transition-opacity" />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
              <Legend verticalAlign="bottom" height={36} iconType="circle" />
            </PieChart>
          ) : activeChart === "status-pie" ? (
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                outerRadius={95}
                dataKey="value"
                stroke="none"
              >
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: '8px' }} />
              <Legend verticalAlign="bottom" height={36} iconType="circle" />
            </PieChart>
          ) : activeChart === "types-bar" ? (
            <BarChart data={typesData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="type" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px' }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
            </BarChart>
          ) : activeChart === "radar" ? (
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="category" tick={{ fill: '#475569', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="Risk Score" dataKey="score" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.4} />
              <Tooltip />
            </RadarChart>
          ) : activeChart === "agent-area" ? (
            <AreaChart data={agentData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip contentStyle={{ borderRadius: '8px' }} />
              <Area type="monotone" dataKey="count" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorCount)" />
            </AreaChart>
          ) : (
            <ComposedChart data={trendData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip contentStyle={{ borderRadius: '8px' }} />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="uploads" barSize={20} fill="#93c5fd" radius={[2, 2, 0, 0]} />
              <Line type="monotone" dataKey="analysis" stroke="#2563eb" strokeWidth={3} dot={{ r: 4, fill: "#2563eb", strokeWidth: 0 }} />
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
