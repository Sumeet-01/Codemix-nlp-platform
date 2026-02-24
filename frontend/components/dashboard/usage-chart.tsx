"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DailyStats } from "@/lib/types";

interface UsageChartProps {
  data: DailyStats[];
}

export function UsageChart({ data }: UsageChartProps) {
  const formatted = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    Total: d.count,
    Sarcasm: d.sarcasm_count,
    Misinformation: d.misinfo_count,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Daily Usage (30 days)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={formatted} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gTotal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0a84ff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0a84ff" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gSarcasm" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff9f0a" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ff9f0a" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gMisinfo" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff453a" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ff453a" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#888" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#888" }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#111", border: "1px solid #222", borderRadius: "8px", fontSize: "12px" }}
              labelStyle={{ color: "#ccc" }}
            />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: "12px", color: "#888" }} />
            <Area type="monotone" dataKey="Total" stroke="#0a84ff" fill="url(#gTotal)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="Sarcasm" stroke="#ff9f0a" fill="url(#gSarcasm)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="Misinformation" stroke="#ff453a" fill="url(#gMisinfo)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
