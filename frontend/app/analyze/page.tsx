"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Send, Trash2, Copy, Download, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { analyzeText, explainText } from "@/lib/api";
import { ResultCard } from "@/components/analysis/result-card";
import { ExplanationView } from "@/components/analysis/explanation-view";
import { ConfidenceMeter } from "@/components/analysis/confidence-meter";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import type { AnalysisResponse, ExplanationResponse } from "@/lib/types";

const analyzeSchema = z.object({
  text: z
    .string()
    .min(1, "Please enter some text to analyze")
    .max(500, "Text must be under 500 characters"),
  model: z.enum(["xlm-roberta", "mbert", "indicbert"]).optional(),
  language: z.string().optional(),
});

type AnalyzeForm = z.infer<typeof analyzeSchema>;

const EXAMPLE_TEXTS = [
  {
    text: "Waah kya development hai 😂 roads toh tut rahe hain lekin neta ji ka bungalow ready ho gaya!",
    label: "Sarcastic Hinglish",
  },
  {
    text: "Scientists discovered that drinking hot water with lemon cures cancer - share before this gets deleted!",
    label: "Misinformation",
  },
  {
    text: "Aaj ka weather bahut accha hai, perfect day for a walk! 🌤️",
    label: "Normal Hinglish",
  },
  {
    text: "Oh sure, because the 50th meeting will definitely solve the problem that 49 didn't 🙄",
    label: "Sarcastic English",
  },
];

export default function AnalyzePage() {
  const { toast } = useToast();
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<AnalyzeForm>({
    resolver: zodResolver(analyzeSchema),
    defaultValues: { text: "", model: "xlm-roberta", language: "auto" },
  });

  const textValue = watch("text");

  const analyzeMutation = useMutation({
    mutationFn: analyzeText,
    onSuccess: (data) => {
      setResult(data);
      setExplanation(null);
      toast({ title: "Analysis complete!", description: "Results are ready." });
    },
    onError: (error: Error) => {
      toast({
        title: "Analysis failed",
        description: error.message || "Please try again.",
        variant: "destructive",
      });
    },
  });

  const explainMutation = useMutation({
    mutationFn: explainText,
    onSuccess: (data) => {
      setExplanation(data);
      toast({ title: "Explanation generated!" });
    },
    onError: (error: Error) => {
      toast({
        title: "Explanation failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: AnalyzeForm) => {
    analyzeMutation.mutate(data);
  };

  const handleExplain = () => {
    if (textValue) {
      explainMutation.mutate({ text: textValue });
    }
  };

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      toast({ title: "Copied to clipboard!" });
    }
  };

  const handleExport = () => {
    if (result) {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis-${result.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-6 lg:p-8 overflow-auto">
          <div className="max-w-6xl mx-auto">
            {/* Page Header */}
            <motion.div
              initial={{ opacity: 0, y: -16 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8"
            >
              <h1 className="text-3xl font-bold mb-2">Analyze Text</h1>
              <p className="text-muted-foreground">
                Detect sarcasm and misinformation in Hinglish, Tanglish, or English text
              </p>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Input Section */}
              <motion.div
                initial={{ opacity: 0, x: -24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="border-border/50">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-base font-semibold">Input Text</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                      <div className="relative">
                        <Textarea
                          {...register("text")}
                          placeholder="Enter text in Hinglish, Tanglish, or English...&#10;&#10;Example: Waah kya development hai 😂 roads toh tut rahe hain"
                          className="min-h-[200px] resize-none bg-secondary/50 border-border/50 focus:border-primary transition-colors text-sm leading-relaxed"
                          maxLength={500}
                        />
                        <span
                          className={`absolute bottom-3 right-3 text-xs ${
                            textValue?.length > 450 ? "text-brand-red" : "text-muted-foreground"
                          }`}
                        >
                          {textValue?.length || 0}/500
                        </span>
                      </div>
                      {errors.text && (
                        <p className="text-brand-red text-xs">{errors.text.message}</p>
                      )}

                      {/* Example texts */}
                      <div>
                        <p className="text-xs text-muted-foreground mb-2">Try an example:</p>
                        <div className="flex flex-wrap gap-2">
                          {EXAMPLE_TEXTS.map((ex) => (
                            <button
                              key={ex.label}
                              type="button"
                              onClick={() => setValue("text", ex.text)}
                              className="text-xs px-2.5 py-1 rounded-full border border-border/50 hover:border-primary/50 hover:text-primary transition-colors"
                            >
                              {ex.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="flex gap-3">
                        <Button
                          type="submit"
                          className="flex-1 bg-brand-blue hover:bg-brand-blue/90 shadow-glow"
                          disabled={analyzeMutation.isPending || !textValue}
                        >
                          {analyzeMutation.isPending ? (
                            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Analyzing...</>
                          ) : (
                            <><Send className="mr-2 h-4 w-4" /> Analyze</>
                          )}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => { reset(); setResult(null); setExplanation(null); }}
                          className="border-border/50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Results Section */}
              <motion.div
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <AnimatePresence mode="wait">
                  {analyzeMutation.isPending ? (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <Card className="border-border/50">
                        <CardContent className="p-6 space-y-4">
                          <div className="skeleton h-6 w-40" />
                          <div className="skeleton h-20 w-full" />
                          <div className="skeleton h-16 w-full" />
                          <div className="skeleton h-16 w-full" />
                        </CardContent>
                      </Card>
                    </motion.div>
                  ) : result ? (
                    <motion.div
                      key="result"
                      initial={{ opacity: 0, scale: 0.97 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      <ResultCard result={result} />
                      <div className="flex gap-2 mt-3">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleExplain}
                          disabled={explainMutation.isPending}
                          className="border-border/50"
                        >
                          {explainMutation.isPending ? (
                            <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Explaining...</>
                          ) : (
                            <><Info className="mr-2 h-3.5 w-3.5" /> Explain</>
                          )}
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleCopy} className="border-border/50">
                          <Copy className="mr-2 h-3.5 w-3.5" /> Copy JSON
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleExport} className="border-border/50">
                          <Download className="mr-2 h-3.5 w-3.5" /> Export
                        </Button>
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="h-full flex items-center justify-center"
                    >
                      <Card className="border-border/50 w-full">
                        <CardContent className="p-12 text-center">
                          <div className="text-4xl mb-4">🔍</div>
                          <p className="text-muted-foreground text-sm">
                            Enter text and click Analyze to see results
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </div>

            {/* Explanation View */}
            <AnimatePresence>
              {explanation && (
                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -16 }}
                  className="mt-8"
                >
                  <ExplanationView explanation={explanation} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
