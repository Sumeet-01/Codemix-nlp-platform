"use client";

import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { Activity, Brain, AlertTriangle, Clock } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentAnalyses } from "@/components/dashboard/recent-analyses";
import { UsageChart } from "@/components/dashboard/usage-chart";
import { getDashboardStats, getHistory } from "@/lib/api";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["history", { page_size: 5 }],
    queryFn: () => getHistory({ page: 1, page_size: 5 }),
  });

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-6 lg:p-8 overflow-auto">
          <div className="max-w-7xl mx-auto space-y-8">
            {/* Page Header */}
            <motion.div
              initial={{ opacity: 0, y: -16 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
              <p className="text-muted-foreground">
                Your analysis overview for the last 30 days
              </p>
            </motion.div>

            {/* Stats Cards */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              {stats && <StatsCards stats={stats} />}
            </motion.div>

            {/* Charts and Recent */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <motion.div
                className="lg:col-span-2"
                initial={{ opacity: 0, x: -24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                {stats && <UsageChart data={stats.daily_stats} />}
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <RecentAnalyses
                  items={history?.items?.slice(0, 5) ?? []}
                />
              </motion.div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
