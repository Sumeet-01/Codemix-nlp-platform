"use client";

import { motion } from "framer-motion";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AttentionHeatmap } from "@/components/analysis/attention-heatmap";
import type { ExplanationResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ExplanationViewProps {
  explanation: ExplanationResponse;
}

export function ExplanationView({ explanation }: ExplanationViewProps) {
  const maxAbsSarcasm = Math.max(...explanation.shap_values.map((v) => Math.abs(v.sarcasm_score)), 0.001);
  const maxAbsMisinfo = Math.max(...explanation.shap_values.map((v) => Math.abs(v.misinfo_score)), 0.001);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1, ease: [0.4, 0, 0.2, 1] }}
    >
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Model Explainability</CardTitle>
          <p className="text-xs text-muted-foreground">
            SHAP attribution scores show which tokens influence each prediction
          </p>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="sarcasm">
            <TabsList className="mb-4">
              <TabsTrigger value="sarcasm">Sarcasm SHAP</TabsTrigger>
              <TabsTrigger value="misinfo">Misinfo SHAP</TabsTrigger>
              <TabsTrigger value="attention">Attention</TabsTrigger>
            </TabsList>

            <TabsContent value="sarcasm">
              <div className="flex flex-wrap gap-2">
                {explanation.shap_values.map((sv, i) => {
                  const norm = sv.sarcasm_score / maxAbsSarcasm;
                  const positive = norm > 0;
                  return (
                    <span
                      key={i}
                      title={`SHAP: ${sv.sarcasm_score.toFixed(3)}`}
                      className={cn(
                        "inline-flex px-2 py-1 rounded-md text-sm font-medium transition-colors",
                        positive
                          ? "bg-brand-red/20 text-brand-red border border-brand-red/20"
                          : "bg-brand-green/20 text-brand-green border border-brand-green/20",
                        "opacity-" + Math.max(30, Math.round(Math.abs(norm) * 100))
                      )}
                      style={{ opacity: 0.3 + Math.abs(norm) * 0.7 }}
                    >
                      {sv.token}
                    </span>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                <span className="text-brand-red">Red</span> = pushes toward sarcasm &nbsp;·&nbsp;
                <span className="text-brand-green">Green</span> = pushes toward genuine
              </p>
            </TabsContent>

            <TabsContent value="misinfo">
              <div className="flex flex-wrap gap-2">
                {explanation.shap_values.map((sv, i) => {
                  const norm = sv.misinfo_score / maxAbsMisinfo;
                  const positive = norm > 0;
                  return (
                    <span
                      key={i}
                      title={`SHAP: ${sv.misinfo_score.toFixed(3)}`}
                      className={cn(
                        "inline-flex px-2 py-1 rounded-md text-sm font-medium",
                        positive
                          ? "bg-brand-red/20 text-brand-red border border-brand-red/20"
                          : "bg-brand-green/20 text-brand-green border border-brand-green/20"
                      )}
                      style={{ opacity: 0.3 + Math.abs(norm) * 0.7 }}
                    >
                      {sv.token}
                    </span>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                <span className="text-brand-red">Red</span> = misinformation signal &nbsp;·&nbsp;
                <span className="text-brand-green">Green</span> = credibility signal
              </p>
            </TabsContent>

            <TabsContent value="attention">
              <AttentionHeatmap
                tokens={explanation.tokens}
                weights={explanation.attention_weights}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </motion.div>
  );
}
