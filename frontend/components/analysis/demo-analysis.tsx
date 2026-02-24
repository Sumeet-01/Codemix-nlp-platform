"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ResultCard } from "@/components/analysis/result-card";
import { analyzeText } from "@/lib/api";
import type { AnalysisResponse } from "@/lib/types";

const EXAMPLES = [
  { text: "Haan bilkul, Modi ji ne toh desh ka bohot vikas kar diya 🙄", label: "Sarcastic Hindi" },
  { text: "Waah kya development hai roads tut rahe hain lekin neta ji ka bungalow ready ho gaya!", label: "Sarcastic Hinglish" },
  { text: "Scientists ne proof kar diya ki 5G towers se corona failta hai - share before deleted!", label: "Misinformation" },
  { text: "Aaj weather bahut accha hai, thoda walk karna chahiye", label: "Normal Text" },
];

export function DemoAnalysis() {
  const [text, setText] = useState(EXAMPLES[0].text);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => analyzeText({ text }),
    onSuccess: setResult,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 mb-3">
        {EXAMPLES.map((ex, i) => (
          <button
            key={i}
            onClick={() => { setText(ex.text); setResult(null); }}
            className="text-xs px-3 py-1.5 rounded-full border border-border/50 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
          >
            {ex.label}
          </button>
        ))}
      </div>

      <Textarea
        value={text}
        onChange={(e) => { setText(e.target.value); setResult(null); }}
        placeholder="Type Hinglish text here…"
        className="min-h-[100px] text-sm"
        maxLength={500}
      />

      <Button
        onClick={() => mutation.mutate()}
        disabled={!text.trim() || mutation.isPending}
        className="bg-brand-blue hover:bg-brand-blue/90 shadow-glow gap-2"
      >
        {mutation.isPending ? (
          <><Loader2 className="h-4 w-4 animate-spin" /> Analyzing…</>
        ) : (
          <><Zap className="h-4 w-4" /> Analyze</>
        )}
      </Button>

      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={result.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <ResultCard result={result} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
