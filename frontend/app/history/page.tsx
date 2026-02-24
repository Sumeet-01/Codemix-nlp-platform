"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Clock } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { FilterBar } from "@/components/history/filter-bar";
import { HistoryTable } from "@/components/history/history-table";
import { getHistory } from "@/lib/api";
import type { HistoryFilters } from "@/lib/types";

export default function HistoryPage() {
  const [filters, setFilters] = useState<HistoryFilters>({ page: 1, page_size: 20 });

  const { data, isLoading } = useQuery({
    queryKey: ["history", filters],
    queryFn: () => getHistory(filters),
  });

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <div className="flex flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 gap-6">
        <Sidebar />
        <main className="flex-1 min-w-0 space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-xl bg-brand-blue/15 flex items-center justify-center">
                <Clock className="h-5 w-5 text-brand-blue" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Analysis History</h1>
                <p className="text-sm text-muted-foreground">
                  {data?.total ?? 0} total analyses
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <FilterBar filters={filters} onChange={setFilters} />
              <HistoryTable
                data={data}
                isLoading={isLoading}
                page={filters.page ?? 1}
                onPageChange={(p) => setFilters({ ...filters, page: p })}
              />
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
