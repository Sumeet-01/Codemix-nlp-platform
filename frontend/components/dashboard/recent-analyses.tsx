"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { truncate, formatRelativeTime } from "@/lib/utils";
import type { AnalysisResponse } from "@/lib/types";
import { ArrowRight } from "lucide-react";

interface RecentAnalysesProps {
  items: AnalysisResponse[];
}

export function RecentAnalyses({ items }: RecentAnalysesProps) {
  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-base">Recent Analyses</CardTitle>
        <Link href="/history">
          <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground text-xs">
            View all <ArrowRight className="h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="space-y-1 p-0">
        {items.length === 0 && (
          <p className="text-sm text-muted-foreground px-6 pb-5">No analyses yet.</p>
        )}
        {items.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04, duration: 0.25 }}
            className="flex items-center gap-3 px-6 py-3 hover:bg-secondary/30 transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm truncate">{truncate(item.text, 80)}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {formatRelativeTime(item.created_at)}
              </p>
            </div>
            <div className="flex gap-1.5 shrink-0">
              <Badge variant={item.sarcasm.label === "SARCASTIC" ? "sarcasm" : "safe"} className="text-[10px]">
                {item.sarcasm.label === "SARCASTIC" ? "S" : "✓"}
              </Badge>
              <Badge variant={item.misinformation.label === "MISINFORMATION" ? "misinfo" : "safe"} className="text-[10px]">
                {item.misinformation.label === "MISINFORMATION" ? "M" : "✓"}
              </Badge>
            </div>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  );
}
