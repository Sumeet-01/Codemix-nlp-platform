"use client";

import { useRef, useEffect } from "react";

interface AttentionHeatmapProps {
  tokens: string[];
  weights: number[][];
}

function interpolateColor(value: number): string {
  // 0 → low (dark), 1 → high (blue)
  const r = Math.round(10 + value * 0 );
  const g = Math.round(132 * value);
  const b = Math.round(value * 255);
  return `rgb(${r},${g},${b})`;
}

export function AttentionHeatmap({ tokens, weights }: AttentionHeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const CELL = 28;
  const PAD = 60;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !weights.length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const n = Math.min(tokens.length, weights.length, 20);
    const size = n * CELL + PAD;
    canvas.width = size;
    canvas.height = size;

    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, size, size);

    // Find max
    let maxW = 0;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if ((weights[i]?.[j] ?? 0) > maxW) maxW = weights[i][j];
      }
    }

    // Draw cells
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const val = maxW > 0 ? (weights[i]?.[j] ?? 0) / maxW : 0;
        ctx.fillStyle = interpolateColor(val);
        ctx.fillRect(PAD + j * CELL, PAD + i * CELL, CELL - 1, CELL - 1);
      }
    }

    // Labels
    ctx.fillStyle = "#888";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "right";
    for (let i = 0; i < n; i++) {
      ctx.fillText(tokens[i]?.slice(0, 8) ?? "", PAD - 4, PAD + i * CELL + CELL / 2 + 3);
    }
    ctx.textAlign = "center";
    for (let j = 0; j < n; j++) {
      ctx.save();
      ctx.translate(PAD + j * CELL + CELL / 2, PAD - 4);
      ctx.rotate(-Math.PI / 4);
      ctx.fillText(tokens[j]?.slice(0, 8) ?? "", 0, 0);
      ctx.restore();
    }
  }, [tokens, weights]);

  return (
    <div className="overflow-auto rounded-lg bg-black/50 p-3">
      <canvas ref={canvasRef} className="rounded" />
      <p className="text-xs text-muted-foreground mt-2">
        Self-attention weights from last transformer layer (top 20 tokens). Brighter = higher attention.
      </p>
    </div>
  );
}
