"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

const data = [
  { name: "Low Risk", value: 15, color: "#10b981" }, // emerald-500
  { name: "Medium Risk", value: 6, color: "#f59e0b" }, // amber-500
  { name: "High Risk", value: 3, color: "#f43f5e" }, // rose-500
];

export function RiskOverview() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 shadow-sm flex flex-col h-[380px]">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Risk Distribution</h2>
        <p className="text-sm text-slate-500 mt-1">Across all analyzed contracts.</p>
      </div>
      <div className="flex-1 w-full relative min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', padding: '8px 12px' }}
              itemStyle={{ color: '#0f172a', fontWeight: 500, fontSize: '14px' }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: '13px', color: '#64748b' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
