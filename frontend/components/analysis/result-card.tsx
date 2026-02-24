"use client";

import { motion } from "framer-motion";
import { Clock, Cpu, CheckCircle, AlertTriangle, TrendingUp, ShieldCheck, ShieldAlert, MessageCircleWarning, MessageCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceMeter } from "@/components/analysis/confidence-meter";
import { formatMs } from "@/lib/utils";
import type { AnalysisResponse } from "@/lib/types";

interface ResultCardProps {
  result: AnalysisResponse;
}

function getSarcasmDescription(score: number, label: string): string {
  if (label === "SARCASTIC") {
    if (score >= 0.85) return "Strong sarcastic tone detected — ironic or mocking intent is highly likely.";
    if (score >= 0.65) return "Sarcastic indicators found — text likely contains irony or mockery.";
    return "Mild sarcastic signals present — text may contain subtle irony.";
  }
  if (score <= 0.10) return "No sarcasm detected — text appears genuine and straightforward.";
  if (score <= 0.30) return "Very low sarcasm probability — text is likely sincere.";
  return "Borderline — some ambiguous signals but likely not sarcastic.";
}

function getMisinfoDescription(score: number, label: string): string {
  if (label === "MISINFORMATION") {
    if (score >= 0.85) return "High misinformation risk — contains unverified claims, urgency language, or viral patterns.";
    if (score >= 0.65) return "Likely misinformation — suspicious claims or misleading language detected.";
    return "Some misinformation signals — claims should be verified from trusted sources.";
  }
  if (score <= 0.10) return "Content appears reliable — no misinformation indicators found.";
  if (score <= 0.30) return "Low misinformation risk — content seems factual.";
  return "Borderline — some claims may need independent verification.";
}

export function ResultCard({ result }: ResultCardProps) {
  const isSarcastic = result.sarcasm.label === "SARCASTIC";
  const isMisinformation = result.misinformation.label === "MISINFORMATION";

  const sarcasmDesc = getSarcasmDescription(result.sarcasm.score, result.sarcasm.label);
  const misinfoDesc = getMisinfoDescription(result.misinformation.score, result.misinformation.label);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
    >
      <Card className="overflow-hidden">
        {/* Gradient accent bar */}
        <div
          className={`h-1.5 w-full ${
            isMisinformation
              ? "bg-gradient-to-r from-brand-red to-brand-orange"
              : isSarcastic
              ? "bg-gradient-to-r from-brand-orange to-yellow-500"
              : "bg-gradient-to-r from-brand-green to-teal-500"
          }`}
        />

        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base font-semibold mb-2">
                Analysis Result
              </CardTitle>
              <p className="text-sm text-muted-foreground line-clamp-3">{result.text}</p>
            </div>
            <div className="flex gap-2 shrink-0">
              <Badge variant={isSarcastic ? "sarcasm" : "safe"} className="flex items-center gap-1">
                {isSarcastic ? (
                  <><MessageCircleWarning className="h-3 w-3" /> Sarcastic</>
                ) : (
                  <><MessageCircle className="h-3 w-3" /> Not Sarcastic</>
                )}
              </Badge>
              <Badge variant={isMisinformation ? "misinfo" : "safe"} className="flex items-center gap-1">
                {isMisinformation ? (
                  <><ShieldAlert className="h-3 w-3" /> Misinformation</>
                ) : (
                  <><ShieldCheck className="h-3 w-3" /> Reliable</>
                )}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Scores */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* Sarcasm Score */}
            <div className={`rounded-xl p-4 border ${
              isSarcastic
                ? "bg-orange-500/5 border-orange-500/20"
                : "bg-green-500/5 border-green-500/20"
            }`}>
              <div className="flex items-center gap-4 mb-3">
                <ConfidenceMeter
                  value={result.sarcasm.score}
                  label=""
                  size="md"
                />
                <div className="flex-1">
                  <p className="font-semibold text-sm mb-0.5">
                    {isSarcastic ? "Sarcasm Detected" : "No Sarcasm"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Score: {Math.round(result.sarcasm.score * 100)}% · Confidence: {result.sarcasm.confidence}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{sarcasmDesc}</p>
            </div>

            {/* Misinformation Score */}
            <div className={`rounded-xl p-4 border ${
              isMisinformation
                ? "bg-red-500/5 border-red-500/20"
                : "bg-green-500/5 border-green-500/20"
            }`}>
              <div className="flex items-center gap-4 mb-3">
                <ConfidenceMeter
                  value={result.misinformation.score}
                  label=""
                  size="md"
                />
                <div className="flex-1">
                  <p className="font-semibold text-sm mb-0.5">
                    {isMisinformation ? "Misinformation Detected" : "Content Reliable"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Score: {Math.round(result.misinformation.score * 100)}% · Confidence: {result.misinformation.confidence}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{misinfoDesc}</p>
            </div>
          </div>

          {/* Language Detection */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/30 mb-3">
            <span className="text-xs font-medium text-muted-foreground">Language Detected:</span>
            <Badge variant="outline" className="text-xs capitalize">
              {result.language === "hinglish" ? "🇮🇳 Hinglish (Hindi-English)" :
               result.language === "tanglish" ? "🇮🇳 Tanglish (Tamil-English)" :
               result.language === "english" ? "🇬🇧 English" :
               "🌐 Auto-detected"}
            </Badge>
          </div>

          {/* Metadata */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground border-t border-border/40 pt-3">
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" />
              {formatMs(result.processing_time_ms)}
            </span>
            <span className="flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5" />
              XLM-RoBERTa ({result.model_version})
            </span>
            {result.is_cached && (
              <span className="flex items-center gap-1.5 text-brand-green">
                <CheckCircle className="h-3.5 w-3.5" />
                Cached Result
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
