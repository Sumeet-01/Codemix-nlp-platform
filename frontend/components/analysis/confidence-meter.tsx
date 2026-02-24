"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ConfidenceMeterProps {
  value: number; // 0-1
  label?: string;
  size?: "sm" | "md" | "lg";
  color?: string;
  className?: string;
}

const sizeMap = { sm: 56, md: 80, lg: 100 };
const strokeWidthMap = { sm: 5, md: 6, lg: 7 };

export function ConfidenceMeter({
  value,
  label,
  size = "md",
  color,
  className,
}: ConfidenceMeterProps) {
  const dim = sizeMap[size];
  const sw = strokeWidthMap[size];
  const r = (dim - sw * 2) / 2;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference - circumference * Math.min(1, Math.max(0, value));

  const autoColor =
    color ??
    (value >= 0.75
      ? "hsl(var(--brand-red))"
      : value >= 0.45
      ? "hsl(var(--brand-orange))"
      : "hsl(var(--brand-green))");

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <svg width={dim} height={dim} className="-rotate-90">
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth={sw}
          strokeLinecap="round"
        />
        <motion.circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke={autoColor}
          strokeWidth={sw}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: dashOffset }}
          transition={{ duration: 0.9, ease: [0.4, 0, 0.2, 1] }}
        />
        <text
          x={dim / 2}
          y={dim / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          className="rotate-90 fill-foreground font-semibold"
          style={{ fontSize: size === "sm" ? "12px" : size === "md" ? "16px" : "20px", transform: `rotate(90deg) translate(0,0)`, transformOrigin: "center" }}
        >
          {Math.round(value * 100)}%
        </text>
      </svg>
      {label && (
        <span className="text-xs text-muted-foreground text-center">{label}</span>
      )}
    </div>
  );
}
