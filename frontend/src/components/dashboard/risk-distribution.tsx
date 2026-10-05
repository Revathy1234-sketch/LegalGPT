"use client";

import { useState } from "react";
import { useContext } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, Area, AreaChart,
  Treemap,
} from "recharts";
import { EvidenceContext } from "@/src/contexts/evidence-context";
import { RiskDistribution as RiskSlice } from "@/src/lib/api/dashboard";
import { ChevronDown, BarChart3, PieChart as PieIcon, Activity, TrendingUp, Grid, Radar as RadarIcon } from "lucide-react";

interface Props {
  data: RiskSlice[];
  title?: string;
  subtitle?: string;
  height?: number;
  // Extended dashboard data for additional charts
  statusDistribution?: { name: string; value: number; color: string }[];
  contractTypes?: { type: string; count: number }[];
  riskRadar?: { category: string; score: number }[];
  agentUsage?: { name: string; count: number }[];
  defaultChartType?: ChartType;
}

type ChartType = "donut" | "bar" | "area" | "treemap" | "radar" | "breakdown" | "stacked" | "histogram";

const CHART_OPTIONS: { value: ChartType; label: string; description: string; icon: typeof PieIcon }[] = [
  { value: "donut",     label: "Risk Donut",          description: "Risk severity distribution (donut)",     icon: PieIcon },
  { value: "bar",       label: "Risk Bar Chart",       description: "Risk counts as horizontal bars",         icon: BarChart3 },
  { value: "stacked",   label: "Risk Stacked Bar",     description: "Stacked risk counts by category",        icon: BarChart3 },
  { value: "histogram", label: "Risk Histogram",       description: "Distribution of risk scores",            icon: BarChart3 },
  { value: "area",      label: "Risk Trend (Area)",    description: "Cumulative risk area chart",             icon: TrendingUp },
  { value: "treemap",   label: "Risk Treemap",         description: "Area-proportional risk breakdown",       icon: Grid },
  { value: "radar",     label: "Derived Risk Vectors", description: "Multi-category risk (derived weighting)",icon: RadarIcon },
  { value: "breakdown", label: "Contract Status",      description: "Processed vs. pending status split",     icon: Activity },
];

// Breakdown slices for each risk finding category
function buildBreakdown(data: RiskSlice[]) {
  const counts: Record<string, number> = {};
  data.forEach((slice) => {
    (slice.findings || []).forEach((f) => {
      const cat = String(f.category || "Other");
      counts[cat] = (counts[cat] || 0) + 1;
    });
  });
  if (Object.keys(counts).length === 0) {
    return data.map((s) => ({ name: s.name, value: s.value, fill: s.color }));
  }
  const palette = ["#3b82f6", "#8b5cf6", "#06b6d4", "#f59e0b", "#10b981", "#ec4899", "#f43f5e", "#6366f1"];
  return Object.entries(counts).map(([name, value], i) => ({
    name, value, fill: palette[i % palette.length],
  }));
}

// Area/Line data: cumulative across severity
function buildAreaData(data: RiskSlice[]) {
  const totalVal = data.reduce((sum, d) => sum + d.value, 0) || 1;
  return data.map((d, i) => {
    const cumulative = data.slice(0, i + 1).reduce((s, x) => s + x.value, 0);
    return {
      name: d.name,
      value: d.value,
      cumulative,
      total: totalVal,
      pct: Math.round((d.value / totalVal) * 100),
    };
  });
}

export function RiskDistributionChart({
  data,
  title = "Risk Distribution",
  subtitle = "Findings grouped by severity — click a slice to see the PDF proof.",
  height = 340,
  statusDistribution,
  contractTypes,
  riskRadar,
  agentUsage,
  defaultChartType = "donut",
}: Props) {
  const evidenceContext = useContext(EvidenceContext);
  const [chartType, setChartType] = useState<ChartType>(defaultChartType);
  const [open, setOpen] = useState(false);

  const total = (data || []).reduce((sum, slice) => sum + (slice.value || 0), 0);

  const handleSliceClick = (node: unknown) => {
    if (!evidenceContext) return;
    const entry = (node as { payload?: RiskSlice })?.payload ?? (node as RiskSlice);
    if (!entry) return;
    const findings = entry.findings || [];
    if (findings.length === 0) { evidenceContext.clearEvidence(); return; }
    const mapped = findings.map((f, i) => ({
      id: `finding-${i}`,
      agent: "Risk Analysis",
      finding: String(f.description || f.category || "Risk finding").slice(0, 90),
      severity: f.severity || entry.name,
      explanation: String(f.mitigation || f.impact || "Identified by the Risk Analysis agent in the uploaded PDF.").slice(0, 300),
      page: f.page || f.evidence || "PDF",
      section: f.section || f.category || "",
      sourceText: String(f.source_text || f.description || "No verbatim passage captured.").slice(0, 500),
      highlight: String(f.source_text || "").split(/(?<=[.!?])\s/)[0]?.slice(0, 200) || "",
    }));
    evidenceContext.setSourceType(`Risk Analysis · ${entry.name}`);
    evidenceContext.setEvidence(mapped);
    evidenceContext.setIsOpen(true);
  };

  const current = CHART_OPTIONS.find((o) => o.value === chartType)!;
  const CurrentIcon = current.icon;

  // Radar data (use custom riskRadar if provided, else derive from risk slices)
  const radarData = riskRadar && riskRadar.length > 0
    ? riskRadar
    : [
        { category: "Financial", score: data.find((d) => d.name.toLowerCase().includes("high"))?.value ?? 0 },
        { category: "Operational", score: data.find((d) => d.name.toLowerCase().includes("medium"))?.value ?? 0 },
        { category: "Legal", score: Math.round((data.find((d) => d.name.toLowerCase().includes("high"))?.value ?? 0) * 1.3) },
        { category: "Compliance", score: (data[0]?.value ?? 0) + (data[1]?.value ?? 0) },
        { category: "Reputation", score: data.find((d) => d.name.toLowerCase().includes("low"))?.value ?? 0 },
      ];

  // Status data
  const statusData = statusDistribution && statusDistribution.length > 0
    ? statusDistribution
    : [
        { name: "Processed", value: total, color: "#10b981" },
        { name: "Pending", value: Math.max(0, 2 - total), color: "#f59e0b" },
      ];

  const breakdownData = buildBreakdown(data);
  const areaData = buildAreaData(data);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col" style={{ height }}>
      {/* Header with chart selector */}
      <div className="mb-3 shrink-0 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <p className="text-sm text-slate-700/60 mt-0.5">{current.description}</p>
        </div>

        {/* Dropdown */}
        <div className="relative">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors text-slate-700 outline-none focus:ring-2 focus:ring-blue-500 shrink-0"
          >
            <CurrentIcon className="h-3.5 w-3.5" />
            {current.label}
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
          </button>
          {open && (
            <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-slate-200 rounded-xl shadow-lg w-56 py-1 overflow-hidden">
              {CHART_OPTIONS.map((opt) => {
                const OptIcon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    onClick={() => { setChartType(opt.value); setOpen(false); }}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left hover:bg-slate-50 transition-colors ${
                      chartType === opt.value ? "bg-blue-50 text-blue-600/90" : "text-slate-700"
                    }`}
                  >
                    <OptIcon className="h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">{opt.label}</p>
                      <p className="text-[10px] text-slate-700/40 leading-tight">{opt.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Chart area */}
      {total === 0 && chartType !== "breakdown" && chartType !== "radar" ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-700/40 text-sm text-center gap-2">
          <div className="h-16 w-16 rounded-full border-4 border-dashed border-slate-200" />
          <p className="font-medium text-slate-700/60">No risk findings yet</p>
          <p className="text-xs max-w-[240px]">Run the Risk Analysis agent to populate this chart.</p>
        </div>
      ) : (
        <div className="flex-1 w-full min-h-0 mt-1">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === "donut" ? (
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  innerRadius="50%" outerRadius="80%" paddingAngle={3} stroke="none"
                  onClick={handleSliceClick} cursor="pointer">
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} className="hover:opacity-80 transition-opacity" />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n, props) => [`${v} / ${total} findings (${Math.round((Number(v)/total)*100)}%)`, String(n)]}
                  contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Legend verticalAlign="bottom" height={32} iconType="circle" />
              </PieChart>
            ) : chartType === "bar" ? (
              <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} width={90} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={22} onClick={handleSliceClick} cursor="pointer">
                  {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            ) : chartType === "area" ? (
              <AreaChart data={areaData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} formatter={(v, n, props) => {
                  if (n === 'pct') return [`${props.payload.value} / ${props.payload.total} findings (${v}%)`, 'Percentage'];
                  return [`${v} findings`, String(n)];
                }} />
                <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fill="url(#riskGrad)" />
                <Line type="monotone" dataKey="pct" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
              </AreaChart>
            ) : chartType === "stacked" ? (
              <BarChart data={breakdownData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Legend verticalAlign="top" height={32} iconType="circle" />
                <Bar dataKey="value" stackId="a" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : chartType === "histogram" ? (
              <BarChart data={radarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="category" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#64748b" }} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} formatter={(v) => [`Score: ${v}`, "Exposure"]} />
                <Bar dataKey="score" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : chartType === "radar" ? (
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: "#64748b" }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: "#94a3b8" }} />
                <Radar name="Risk" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} />
              </RadarChart>
            ) : chartType === "treemap" ? (
              <Treemap
                data={data.map((d) => ({ name: d.name, size: d.value, color: d.color }))}
                dataKey="size"
                aspectRatio={4 / 3}
                stroke="#fff"
                content={({ x, y, width, height, name, color }: Record<string, unknown>) => {
                  const w = Number(width), h = Number(height);
                  if (w < 30 || h < 30) return <rect x={Number(x)} y={Number(y)} width={w} height={h} style={{ fill: String(color), stroke: "white" }} />;
                  return (
                    <g>
                      <rect x={Number(x)} y={Number(y)} width={w} height={h} style={{ fill: String(color), stroke: "white", strokeWidth: 2 }} />
                      <text x={Number(x) + w / 2} y={Number(y) + h / 2} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize={Math.min(14, w / 5)} fontWeight="600">
                        {String(name)}
                      </text>
                    </g>
                  );
                }}
              />
            ) : (
              /* breakdown / status */
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  outerRadius="75%" paddingAngle={2} stroke="none">
                  {statusData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip formatter={(v, n) => {
                  const totalContracts = statusData.reduce((sum, d) => sum + d.value, 0);
                  return [`${v} / ${totalContracts} contracts (${Math.round((Number(v)/totalContracts)*100)}%)`, String(n)];
                }} contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: 12 }} />
                <Legend verticalAlign="bottom" height={32} iconType="circle" />
              </PieChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
