"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { motion } from "framer-motion";
import { BrainCircuit, Search, Loader2, TrendingUp, Zap, Target, BookOpen } from "lucide-react";

export default function NicheReportPage() {
  const [keyword, setKeyword] = useState("");
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = async () => {
    if (!keyword.trim()) return;
    setLoading(true);
    setError(null);
    setReport(null);

    const { data: ads } = await supabase
      .from("ads")
      .select("title, network, impressions")
      .ilike("title", `%${keyword}%`)
      .order("impressions", { ascending: false })
      .limit(20);

    if (!ads || ads.length === 0) {
      setError("No ads found for this keyword. Try a broader term.");
      setLoading(false);
      return;
    }

    const res = await fetch("/api/ai/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword, ads }),
    });

    if (res.ok) {
      const data = await res.json();
      setReport(data);
    } else {
      setError("AI analysis failed. Please check your API key.");
    }
    setLoading(false);
  };

  return (
    <div className="max-w-4xl space-y-8 pb-12">
      <div>
        <h1 className="text-4xl font-bold font-syne uppercase tracking-tighter">Niche Intelligence</h1>
        <p className="text-neutral-500 mt-2">Enter any keyword to analyze winning angles in your niche.</p>
      </div>

      <div className="bg-card border border-border rounded-3xl p-8 space-y-6">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-3.5 text-neutral-500" size={18} />
            <input
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && generateReport()}
              placeholder='e.g. "diabetes", "weight loss", "investing"'
              className="w-full bg-neutral-900 border border-border rounded-xl py-3 pl-12 pr-4 focus:border-primary outline-none transition-all"
            />
          </div>
          <button
            onClick={generateReport}
            disabled={loading || !keyword.trim()}
            className="bg-primary hover:bg-primary/90 disabled:opacity-50 px-8 py-3 rounded-xl font-bold flex items-center gap-2 transition-all"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <BrainCircuit size={18} />}
            {loading ? "Analyzing..." : "Run Report"}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}
      </div>

      {report && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-card border border-border rounded-3xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-secondary">
                <Target size={20} />
                <h3 className="font-bold font-syne uppercase tracking-wide">Top Hooks</h3>
              </div>
              <div className="space-y-2">
                {(report.top_hooks || []).map((hook: string, i: number) => (
                  <div key={i} className="flex items-center gap-3 bg-neutral-900/50 p-3 rounded-xl">
                    <span className="text-secondary font-black text-xs w-5 text-center">{i + 1}</span>
                    <span className="text-sm text-neutral-300">{hook}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-card border border-border rounded-3xl p-6 space-y-4">
              <div className="flex items-center gap-2 text-primary">
                <Zap size={20} />
                <h3 className="font-bold font-syne uppercase tracking-wide">Dominant Angle</h3>
              </div>
              <p className="text-neutral-300 text-sm leading-relaxed p-4 bg-primary/5 border border-primary/10 rounded-xl">
                {report.dominant_angle}
              </p>
              <div className="flex items-center gap-2 text-accent mt-4">
                <TrendingUp size={18} />
                <h3 className="font-bold uppercase tracking-wide text-sm">Pattern Detected</h3>
              </div>
              <p className="text-neutral-400 text-sm leading-relaxed">{report.pattern}</p>
            </div>
          </div>

          <div className="bg-primary/10 border border-primary/30 rounded-3xl p-8">
            <div className="flex items-center gap-2 text-primary mb-4">
              <BookOpen size={20} />
              <h3 className="font-bold font-syne uppercase tracking-wide">Strategic Recommendation</h3>
            </div>
            <p className="text-neutral-200 leading-relaxed text-base">{report.recommendation}</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
