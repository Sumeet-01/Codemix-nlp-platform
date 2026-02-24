"use client";

import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime, formatMs, truncate } from "@/lib/utils";
import type { HistoryResponse } from "@/lib/types";

interface HistoryTableProps {
  data: HistoryResponse | undefined;
  isLoading: boolean;
  page: number;
  onPageChange: (page: number) => void;
}

export function HistoryTable({ data, isLoading, page, onPageChange }: HistoryTableProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <p className="text-base font-medium">No analyses found</p>
        <p className="text-sm mt-1">Run an analysis to see results here</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        {data.items.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03, duration: 0.25 }}
            className="flex items-center gap-4 p-4 rounded-xl border border-border/40 bg-card hover:border-border/60 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{truncate(item.text, 100)}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {formatRelativeTime(item.created_at)} · {formatMs(item.processing_time_ms)} · {item.language}
              </p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Badge variant={item.sarcasm.label === "SARCASTIC" ? "sarcasm" : "safe"}>
                {item.sarcasm.label === "SARCASTIC" ? "Sarcastic" : "Genuine"}
              </Badge>
              <Badge variant={item.misinformation.label === "MISINFORMATION" ? "misinfo" : "safe"}>
                {item.misinformation.label === "MISINFORMATION" ? "Misinfo" : "Credible"}
              </Badge>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Pagination */}
      {data.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-muted-foreground">
            {data.total} results · Page {data.page} of {data.total_pages}
          </p>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              disabled={page >= data.total_pages}
              onClick={() => onPageChange(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
