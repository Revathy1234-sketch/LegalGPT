"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

interface Props {
  data: { name: string; count: number }[];
  height?: number;
}

/** Compact, calm agent-execution bar chart. */
export function AgentUsageMini({ data, height = 180 }: Props) {
  const hasData = (data || []).length > 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col" style={{ height }}>
      <div className="mb-2 shrink-0">
        <h3 className="text-sm font-semibold text-slate-900">Agent Executions</h3>
        <p className="text-xs text-slate-700/60 mt-0.5">Runs logged per agent.</p>
      </div>
      {hasData ? (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#64748b" }} interval={0} angle={-20} textAnchor="end" height={45} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#64748b" }} allowDecimals={false} />
              <Tooltip
                cursor={{ fill: "#f8fafc" }}
                contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]} barSize={18}>
                {data.map((_, i) => (
                  <Cell key={i} fill={["#3b82f6", "#6366f1", "#0ea5e9", "#8b5cf6", "#10b981", "#f59e0b"][i % 6]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-xs text-slate-700/40 text-center px-2">
          No agent runs logged yet.
        </div>
      )}
    </div>
  );
}
