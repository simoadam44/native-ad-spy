"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, BrainCircuit, Zap, Target, MessageSquare,
  Star, Copy, CheckCircle2, Loader2, ExternalLink, Heart, RefreshCw
} from "lucide-react";

interface AdModalProps {
  ad: any;
  isOpen: boolean;
  onClose: () => void;
}

export default function AdModal({ ad, isOpen, onClose }: AdModalProps) {
  const [analysis, setAnalysis] = useState<any>(null);
  const [headlines, setHeadlines] = useState<string[]>([]);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingHeadlines, setLoadingHeadlines] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [isFav, setIsFav] = useState(false);
  const [resolving, setResolving] = useState(false);

  // Resolve MGID tracking links via server-side proxy
  const resolveAndVisit = async (landingUrl: string, sourceUrl: string) => {
    const isTracking = landingUrl.includes("clck.mgid.com") || landingUrl.includes("clck.adskeeper.com");
    if (!isTracking) {
      console.log("[AdModal] Direct link, opening:", landingUrl);
      window.open(landingUrl, "_blank");
      return;
    }

    setResolving(true);
    console.log("[AdModal] Resolving tracking link...", { landingUrl, sourceUrl });

    try {
      // Use ad.source as the definitive Referer
      const finalRef = ad.source || sourceUrl || "https://brainberries.co/";
      const ref = encodeURIComponent(finalRef);
      
      const res = await fetch(`/api/resolve?url=${encodeURIComponent(landingUrl)}&ref=${ref}`);
      
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      
      const data = await res.json();
      console.log("[AdModal] Resolved to:", data.url || data.resolved);
      
      const finalUrl = data.url || data.resolved;
      
      if (finalUrl && !finalUrl.includes('clck.mgid.com') && !finalUrl.includes('ploynest.com')) {
        window.open(finalUrl, "_blank");
      } else {
        console.warn("[AdModal] Resolution returned bogus or tracking link, fallback to raw.");
        window.open(landingUrl, "_blank");
      }
    } catch (err) {
      console.error("[AdModal] Resolution failed. Opening raw link as fallback.", err);
      window.open(landingUrl, "_blank");
    } finally {
      setResolving(false);
    }
  };

  const fetchAnalysis = useCallback(async () => {
    if (!ad) return;
    setLoadingAnalysis(true);
    setAnalysis(null);
    try {
      const res = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: ad.title, network: ad.network, landing: ad.landing }),
      });
      if (res.ok) {
        const data = await res.json();
        setAnalysis(data);
      }
    } catch {}
    setLoadingAnalysis(false);
  }, [ad]);

  const fetchHeadlines = useCallback(async () => {
    if (!ad) return;
    setLoadingHeadlines(true);
    setHeadlines([]);
    try {
      const res = await fetch("/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: ad.title }),
      });
      if (res.ok) {
        const data = await res.json();
        setHeadlines(Array.isArray(data) ? data : []);
      }
    } catch {}
    setLoadingHeadlines(false);
  }, [ad]);

  // Auto-trigger both when modal opens
  useEffect(() => {
    if (isOpen && ad) {
      setAnalysis(null);
      setHeadlines([]);
      fetchAnalysis();
      fetchHeadlines();
    }
  }, [isOpen, ad]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  };

  if (!isOpen || !ad) return null;

  const scoreColor = analysis?.score >= 8 ? "text-green-400" : analysis?.score >= 5 ? "text-yellow-400" : "text-red-400";

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="bg-[#13131A] border border-white/10 w-full max-w-5xl max-h-[90vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl shadow-black/60"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-white/3 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase shrink-0 ${(
                { Taboola: 'bg-blue-600', MGID: 'bg-purple-600',
                  Outbrain: 'bg-orange-600', Revcontent: 'bg-green-600'
                } as Record<string, string>
              )[ad.network] || 'bg-neutral-700'} text-white`}>
                {ad.network}
              </span>
              <h2 className="font-bold text-base font-syne truncate">{ad.title}</h2>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-all shrink-0 ml-2">
              <X size={18} />
            </button>
          </div>

          {/* Body — scrollable */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* ── Left: Image + Meta ── */}
              <div className="space-y-4">
                <div className="aspect-video rounded-2xl overflow-hidden border border-white/5 relative group">
                  <img
                    src={ad.image || `https://picsum.photos/seed/${ad.id}/600/340`}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    alt={ad.title}
                    onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/42/600/340`; }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-all flex items-end justify-center pb-4">
                    <button 
                      onClick={() => resolveAndVisit(ad.landing, ad.source || "")}
                      className="bg-white text-black font-bold px-5 py-2 rounded-full text-sm flex items-center gap-2 hover:scale-105 transition-transform"
                    >
                      <ExternalLink size={14} /> Visit Landing Page
                    </button>
                  </div>
                </div>

                {/* Headline card */}
                <div className="bg-neutral-900/60 rounded-2xl border border-white/5 p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">Headline</span>
                    <button onClick={() => copyToClipboard(ad.title)} className="text-neutral-500 hover:text-white transition-all">
                      {copied === ad.title ? <CheckCircle2 size={14} className="text-green-500" /> : <Copy size={14} />}
                    </button>
                  </div>
                  <p className="text-sm font-bold font-syne leading-snug">{ad.title}</p>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">Impressions</p>
                    <p className="text-lg font-bold text-primary mt-0.5">{(ad.impressions || 0).toLocaleString()}</p>
                  </div>
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">Network</p>
                    <p className="text-sm font-bold mt-0.5">{ad.network}</p>
                  </div>
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">First Seen</p>
                    <p className="text-sm font-bold mt-0.5">
                      {new Date(ad.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}
                    </p>
                  </div>
                </div>

                {/* Fav + Visit */}
                <div className="flex gap-3">
                  <button
                    onClick={() => setIsFav(!isFav)}
                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border font-bold text-sm transition-all ${isFav ? 'border-red-500/50 bg-red-500/10 text-red-400' : 'border-border bg-white/5 hover:border-red-500/30 text-neutral-400'}`}
                  >
                    <Heart size={16} fill={isFav ? "currentColor" : "none"} /> {isFav ? "Saved" : "Save"}
                  </button>
                  <button
                    onClick={() => resolveAndVisit(ad.landing, ad.source || "")}
                    disabled={resolving}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-primary text-white font-bold text-sm hover:bg-primary/90 transition-all disabled:opacity-60"
                  >
                    {resolving ? (
                      <><Loader2 size={16} className="animate-spin" /> Resolving...</>
                    ) : (
                      <><ExternalLink size={16} /> Visit Ad</>
                    )}
                  </button>
                </div>
              </div>

              {/* ── Right: AI Sections ── */}
              <div className="space-y-5">

                {/* Strategic Analysis */}
                <section className="bg-neutral-900/40 border border-white/5 rounded-2xl overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-primary/5">
                    <div className="flex items-center gap-2 text-primary">
                      <BrainCircuit size={16} />
                      <span className="font-black text-xs uppercase tracking-widest">Strategic Analysis</span>
                    </div>
                    <button onClick={fetchAnalysis} disabled={loadingAnalysis}
                      className="text-neutral-600 hover:text-white disabled:opacity-40 transition-all"
                      title="Refresh">
                      <RefreshCw size={13} className={loadingAnalysis ? "animate-spin" : ""} />
                    </button>
                  </div>

                  <div className="p-5 space-y-4">
                    {loadingAnalysis ? (
                      <div className="flex flex-col items-center py-6 gap-3">
                        <Loader2 className="animate-spin text-primary" size={28} />
                        <p className="text-xs text-neutral-500 font-bold uppercase tracking-widest">Claude is analysing…</p>
                      </div>
                    ) : analysis ? (
                      <>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            { label: "Winning Hook", value: analysis.hook, icon: Target, color: "text-secondary" },
                            { label: "Marketing Angle", value: analysis.angle, icon: Zap, color: "text-accent" },
                            { label: "Target Audience", value: analysis.audience, icon: BrainCircuit, color: "text-blue-400" },
                            { label: "CTA Type", value: analysis.cta_type, icon: MessageSquare, color: "text-green-400" },
                          ].map(({ label, value, icon: Icon, color }) => (
                            <div key={label} className="bg-neutral-900 rounded-xl p-3 border border-white/5">
                              <div className={`flex items-center gap-1.5 mb-1.5 ${color}`}>
                                <Icon size={12} />
                                <span className="text-[9px] font-black uppercase tracking-widest">{label}</span>
                              </div>
                              <p className="text-[11px] text-neutral-300 leading-relaxed">{value}</p>
                            </div>
                          ))}
                        </div>

                        {/* Score + Tip */}
                        <div className="bg-primary/10 border border-primary/20 rounded-xl p-4 relative overflow-hidden">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Star size={14} className="text-primary fill-primary" />
                              <span className="text-[10px] font-black uppercase tracking-widest text-primary">Native Spy Score</span>
                            </div>
                            <span className={`text-2xl font-black font-syne ${scoreColor}`}>
                              {analysis.score}<span className="text-sm text-neutral-500 font-bold">/10</span>
                            </span>
                          </div>
                          {/* Score bar */}
                          <div className="w-full h-1.5 bg-neutral-800 rounded-full mb-3">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(analysis.score / 10) * 100}%` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                              className="h-full bg-primary rounded-full"
                            />
                          </div>
                          <p className="text-[11px] italic text-neutral-400 leading-relaxed">💡 {analysis.tip}</p>
                          <div className="absolute top-0 right-0 w-20 h-20 bg-primary/10 blur-3xl rounded-full" />
                        </div>
                      </>
                    ) : (
                      <div className="flex flex-col items-center py-6 gap-2 text-neutral-700">
                        <BrainCircuit size={32} />
                        <p className="text-xs font-bold uppercase tracking-widest">Analysis unavailable</p>
                      </div>
                    )}
                  </div>
                </section>

                {/* Creative Variations */}
                <section className="bg-neutral-900/40 border border-white/5 rounded-2xl overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-secondary/5">
                    <div className="flex items-center gap-2 text-secondary">
                      <MessageSquare size={16} />
                      <span className="font-black text-xs uppercase tracking-widest">Creative Variations</span>
                    </div>
                    <button onClick={fetchHeadlines} disabled={loadingHeadlines}
                      className="text-neutral-600 hover:text-white disabled:opacity-40 transition-all"
                      title="Refresh">
                      <RefreshCw size={13} className={loadingHeadlines ? "animate-spin" : ""} />
                    </button>
                  </div>

                  <div className="p-5 space-y-2">
                    {loadingHeadlines ? (
                      <div className="flex flex-col items-center py-6 gap-3">
                        <Loader2 className="animate-spin text-secondary" size={28} />
                        <p className="text-xs text-neutral-500 font-bold uppercase tracking-widest">Generating variations…</p>
                      </div>
                    ) : headlines.length > 0 ? (
                      headlines.map((h, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.12 }}
                          onClick={() => copyToClipboard(h)}
                          className="group flex items-start gap-3 bg-neutral-900 border border-white/5 hover:border-secondary/40 rounded-xl p-3 cursor-pointer transition-all"
                        >
                          <span className="shrink-0 w-5 h-5 rounded-md bg-secondary/20 text-secondary text-[10px] font-black flex items-center justify-center mt-0.5">
                            {i + 1}
                          </span>
                          <p className="text-xs text-neutral-300 group-hover:text-white transition-colors leading-relaxed flex-1">{h}</p>
                          <div className="shrink-0 text-neutral-600 group-hover:text-secondary transition-all">
                            {copied === h ? <CheckCircle2 size={14} className="text-green-500" /> : <Copy size={14} />}
                          </div>
                        </motion.div>
                      ))
                    ) : (
                      <div className="flex flex-col items-center py-6 gap-2 text-neutral-700">
                        <MessageSquare size={32} />
                        <p className="text-xs font-bold uppercase tracking-widest">Variations unavailable</p>
                      </div>
                    )}
                  </div>
                </section>

              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-3 bg-neutral-950 border-t border-white/5 text-center shrink-0">
            <p className="text-[9px] tracking-[0.25em] text-neutral-700 font-bold uppercase">
              Powered by Claude 3.5 Sonnet · Native Spy Intelligence
            </p>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
