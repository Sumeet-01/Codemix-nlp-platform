"use client";

import { useState } from "react";
import { Search, Filter, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { HistoryFilters } from "@/lib/types";

interface FilterBarProps {
  filters: HistoryFilters;
  onChange: (filters: HistoryFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  const [open, setOpen] = useState(false);

  const activeCount = [
    filters.sarcasm_label,
    filters.misinfo_label,
    filters.start_date,
    filters.end_date,
  ].filter(Boolean).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={filters.search ?? ""}
            onChange={(e) => onChange({ ...filters, search: e.target.value, page: 1 })}
            placeholder="Search analyses…"
            className="pl-9 h-10"
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOpen(!open)}
          className="gap-2 h-10"
        >
          <Filter className="h-4 w-4" />
          Filters
          {activeCount > 0 && (
            <Badge variant="default" className="h-5 w-5 p-0 flex items-center justify-center text-[10px]">
              {activeCount}
            </Badge>
          )}
        </Button>
      </div>

      {open && (
        <div className="p-4 border border-border/50 rounded-xl bg-secondary/20 space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Sarcasm</label>
              <select
                value={filters.sarcasm_label ?? ""}
                onChange={(e) =>
                  onChange({ ...filters, sarcasm_label: e.target.value as HistoryFilters["sarcasm_label"] || undefined, page: 1 })
                }
                className="w-full h-9 rounded-lg border border-border/50 bg-secondary/50 px-2 text-sm"
              >
                <option value="">All</option>
                <option value="SARCASTIC">Sarcastic</option>
                <option value="NOT_SARCASTIC">Not Sarcastic</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Misinformation</label>
              <select
                value={filters.misinfo_label ?? ""}
                onChange={(e) =>
                  onChange({ ...filters, misinfo_label: e.target.value as HistoryFilters["misinfo_label"] || undefined, page: 1 })
                }
                className="w-full h-9 rounded-lg border border-border/50 bg-secondary/50 px-2 text-sm"
              >
                <option value="">All</option>
                <option value="MISINFORMATION">Misinformation</option>
                <option value="CREDIBLE">Credible</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Start date</label>
              <Input
                type="date"
                value={filters.start_date ?? ""}
                onChange={(e) => onChange({ ...filters, start_date: e.target.value || undefined, page: 1 })}
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">End date</label>
              <Input
                type="date"
                value={filters.end_date ?? ""}
                onChange={(e) => onChange({ ...filters, end_date: e.target.value || undefined, page: 1 })}
                className="h-9 text-sm"
              />
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-muted-foreground text-xs"
            onClick={() => onChange({ page: 1, page_size: filters.page_size })}
          >
            <X className="h-3.5 w-3.5" /> Clear filters
          </Button>
        </div>
      )}
    </div>
  );
}
