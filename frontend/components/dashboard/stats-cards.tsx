"use client";

import { motion } from "framer-motion";
import { BarChart2, AlertTriangle, AlertCircle, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatMs, formatPercent } from "@/lib/utils";
import type { DashboardStats } from "@/lib/types";

interface StatsCardsProps {
  stats: DashboardStats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      label: "Total Analyses",
      value: stats.total_analyses.toLocaleString(),
      icon: BarChart2,
      color: "text-brand-blue",
      bg: "bg-brand-blue/10",
    },
    {
      label: "Sarcasm Detected",
      value: stats.sarcasm_detected.toLocaleString(),
      subtext: `${stats.total_analyses > 0 ? formatPercent(stats.sarcasm_detected / stats.total_analyses) : "—"} of total`,
      icon: AlertTriangle,
      color: "text-brand-orange",
      bg: "bg-brand-orange/10",
    },
    {
      label: "Misinformation",
      value: stats.misinformation_detected.toLocaleString(),
      subtext: `${stats.total_analyses > 0 ? formatPercent(stats.misinformation_detected / stats.total_analyses) : "—"} of total`,
      icon: AlertCircle,
      color: "text-brand-red",
      bg: "bg-brand-red/10",
    },
    {
      label: "Avg Speed",
      value: formatMs(stats.avg_processing_time_ms),
      subtext: `Cache hit: ${formatPercent(stats.cache_hit_rate)}`,
      icon: Zap,
      color: "text-brand-green",
      bg: "bg-brand-green/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
        >
          <Card className="overflow-hidden">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-muted-foreground">{card.label}</span>
                <div className={`w-8 h-8 rounded-lg ${card.bg} flex items-center justify-center`}>
                  <card.icon className={`h-4 w-4 ${card.color}`} />
                </div>
              </div>
              <p className="text-2xl font-bold">{card.value}</p>
              {card.subtext && (
                <p className="text-xs text-muted-foreground mt-1">{card.subtext}</p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
