"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Brain, Shield, Zap, Globe, BarChart3, Code2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { DemoAnalysis } from "@/components/analysis/demo-analysis";
import { getPlatformStats } from "@/lib/api";

const features = [
  {
    icon: Brain,
    title: "XLM-RoBERTa Large",
    description: "Powered by state-of-the-art multilingual transformer fine-tuned on Indian code-mixed text.",
    gradient: "from-blue-500 to-cyan-500",
  },
  {
    icon: Globe,
    title: "Code-Mixed Support",
    description: "Natively understands Hinglish (Hindi-English), Tanglish (Tamil-English), and mixed Indian dialects.",
    gradient: "from-purple-500 to-pink-500",
  },
  {
    icon: Shield,
    title: "Dual Detection",
    description: "Simultaneously detects both sarcasm and misinformation with independent confidence scores.",
    gradient: "from-green-500 to-emerald-500",
  },
  {
    icon: BarChart3,
    title: "SHAP Explainability",
    description: "Understand why the model made a decision with word-level importance scores and attention heatmaps.",
    gradient: "from-orange-500 to-red-500",
  },
  {
    icon: Zap,
    title: "< 500ms Inference",
    description: "Lightning-fast analysis with Redis caching, GPU acceleration, and optimized batch processing.",
    gradient: "from-yellow-500 to-orange-500",
  },
  {
    icon: Code2,
    title: "Developer API",
    description: "RESTful API with OpenAPI docs, API key auth, and Celery-based async batch processing.",
    gradient: "from-teal-500 to-blue-500",
  },
];

const FALLBACK_STATS = [
  { key: "training_samples", value: "10K+", label: "Training Samples" },
  { key: "f1_score", value: ">75%", label: "F1 Score" },
  { key: "languages", value: "3", label: "Languages" },
  { key: "detection_tasks", value: "2", label: "Detection Tasks" },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] } },
};

export default function HomePage() {
  const { data: platformStats } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: getPlatformStats,
    staleTime: 60_000,
    retry: false,
  });

  const stats = platformStats
    ? [
        {
          value: platformStats.training_samples >= 1000
            ? `${(platformStats.training_samples / 1000).toFixed(0)}K+`
            : String(platformStats.training_samples),
          label: "Training Samples",
        },
        {
          value: `${platformStats.f1_score.toFixed(1)}%`,
          label: "F1 Score",
        },
        { value: String(platformStats.languages), label: "Languages" },
        { value: String(platformStats.detection_tasks), label: "Detection Tasks" },
      ]
    : FALLBACK_STATS.map(({ value, label }) => ({ value, label }));

  return (
    <div className="min-h-screen bg-background">
      <Header />

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-32 pb-20 px-4">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-brand-blue/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-blue/5 rounded-full blur-3xl" />
        </div>

        <motion.div
          className="relative max-w-5xl mx-auto text-center"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants} className="mb-6">
            <Badge
              variant="outline"
              className="px-4 py-1.5 text-sm border-brand-blue/30 text-brand-blue bg-brand-blue/10"
            >
              🇮🇳 Indian Code-Mixed NLP Platform
            </Badge>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6"
          >
            Detect{" "}
            <span className="gradient-text-blue">Sarcasm</span>
            {" & "}
            <span className="bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-transparent">
              Misinformation
            </span>
            <br />
            in Hinglish Text
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            Production-grade NLP platform powered by XLM-RoBERTa-large. Understands Hinglish, Tanglish,
            and mixed Indian dialects with full explainability through SHAP and attention visualization.
          </motion.p>

          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="px-8 h-12 text-base font-semibold bg-brand-blue hover:bg-brand-blue/90 shadow-glow">
              <Link href="/analyze">
                Try It Free <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="px-8 h-12 text-base font-semibold border-border/60">
              <Link href="/dashboard">View Dashboard</Link>
            </Button>
          </motion.div>

          {/* Stats */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20 max-w-3xl mx-auto"
          >
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-3xl md:text-4xl font-black gradient-text-blue mb-1">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* Live Demo */}
      <section className="py-20 px-4 bg-card/30">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Try It Right Now</h2>
            <p className="text-muted-foreground text-lg">
              Enter any Hinglish or English text and see real-time analysis
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <DemoAnalysis />
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Enterprise-Grade NLP Infrastructure
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Everything you need to analyze Indian code-mixed text at scale
            </p>
          </motion.div>

          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
          >
            {features.map((feature) => (
              <motion.div key={feature.title} variants={itemVariants}>
                <Card className="p-6 h-full bg-card border-border/50 hover:border-border transition-all duration-250 hover:shadow-card group">
                  <div
                    className={`inline-flex p-2.5 rounded-xl bg-gradient-to-br ${feature.gradient} mb-4 opacity-90 group-hover:opacity-100 transition-opacity`}
                  >
                    <feature.icon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="font-semibold text-base mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
