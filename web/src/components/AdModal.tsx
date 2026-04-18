"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, BrainCircuit, Zap, Target, MessageSquare,
  Star, Copy, CheckCircle2, Loader2, ExternalLink, Heart, RefreshCw,
  Layout, Search, Download, Eye, ChevronDown, Calendar
} from "lucide-react";
import { supabase } from "@/lib/supabase";

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
            <div className="flex items-center gap-2 shrink-0 ml-2">
              <button
                onClick={() => setIsFav(!isFav)}
                className={`p-2 rounded-full transition-all ${isFav ? 'text-red-500 bg-red-500/10' : 'text-neutral-500 hover:bg-white/10 hover:text-white'}`}
                title={isFav ? "Remove from favorites" : "Save to favorites"}
              >
                <Heart size={18} fill={isFav ? "currentColor" : "none"} />
              </button>
              <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-all text-neutral-500 hover:text-white">
                <X size={18} />
              </button>
            </div>
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

                {/* ── Landing Pages Moved Here ── */}
                <section className="bg-neutral-900/40 border border-white/5 rounded-2xl overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-emerald-500/5">
                    <div className="flex items-center gap-2 text-emerald-400">
                      <Layout size={16} />
                      <span className="font-black text-[10px] uppercase tracking-widest">Landing pages</span>
                    </div>
                    <div className="flex items-center gap-2 px-2 py-0.5 bg-neutral-900 border border-white/10 rounded-md text-[9px] text-neutral-500 font-bold uppercase cursor-not-allowed">
                      All <ChevronDown size={10} />
                    </div>
                  </div>

                  <div className="p-4">
                    <div className="space-y-3">
                      <div className="group hover:bg-white/[0.02] transition-colors p-3 rounded-xl border border-white/5 bg-black/20">
                        <div className="flex items-center gap-3 mb-2.5">
                          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                            <Layout size={14} />
                          </div>
                          <div className="flex-1 min-w-0">
                             <div className="flex items-center justify-between gap-2">
                               <p className="text-[11px] font-bold text-white truncate" title={ad.landing}>{ad.landing}</p>
                               <span className={`px-1.5 py-0.5 rounded-[4px] text-[8px] font-black uppercase ${ad.network === 'Taboola' || ad.network === 'TABOOLA' ? 'bg-blue-600/80' : ad.network === 'MGID' ? 'bg-purple-600/80' : 'bg-orange-600/80'} text-white`}>
                                {ad.ad_type || "Ad"}
                              </span>
                             </div>
                             {ad.final_offer_url && (
                               <p className="text-[9px] text-emerald-400 mt-1 truncate font-bold" title={ad.final_offer_url}>
                                 🎯 Offer: {ad.final_offer_url}
                               </p>
                             )}
                             <p className="text-[9px] text-neutral-500 mt-0.5">
                               {ad.first_seen ? `${new Date(ad.first_seen).toLocaleDateString()} .. ` : "Discovery .. "}
                               {new Date().toLocaleDateString()}
                             </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-2.5 border-t border-white/5">
                          <div className="flex items-center gap-2.5">
                            <div className="flex flex-col">
                              <span className="text-[8px] font-black text-neutral-600 uppercase">Shows</span>
                              <span className="text-xs font-bold text-neutral-300">{ad.impressions || 1}</span>
                            </div>
                            <div className="w-px h-6 bg-white/5 mx-1" />
                            <div className="flex items-center gap-2">
                              <button onClick={() => window.open(ad.landing, '_blank')} className="p-1.5 text-neutral-500 hover:text-emerald-400 transition-colors bg-white/5 rounded-md">
                                <Search size={12} />
                              </button>
                              <button onClick={() => copyToClipboard(ad.landing)} className="p-1.5 text-neutral-500 hover:text-emerald-400 transition-colors bg-white/5 rounded-md">
                                <Copy size={12} />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5">
                            <button className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-[9px] font-black uppercase rounded-lg transition-all flex items-center gap-1 group/btn border border-emerald-400/20 shadow-lg shadow-emerald-900/40">
                              <Download size={11} className="group-hover/btn:scale-110 transition-transform" />
                              Zip
                            </button>
                            <button onClick={() => resolveAndVisit(ad.landing, ad.source)} className="p-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-lg transition-all border border-emerald-500/20" title="Show Preview">
                              <Eye size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3 flex flex-col justify-center">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                      <Calendar size={10} className="text-primary" /> First Seen
                    </p>
                    <p className="text-xs font-bold text-white">
                      {new Date(ad.created_at).toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" })}
                    </p>
                  </div>
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3 flex flex-col justify-center">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                      <Target size={10} className="text-amber-500" /> Ad Type
                    </p>
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-white flex items-center gap-2">
                        {ad.ad_type || "Unknown"}
                        {ad.cloaking_type && ad.cloaking_type !== 'none' && (
                          <span className="text-[8px] bg-red-500/20 text-red-500 px-1 rounded border border-red-500/20">CLOAKED</span>
                        )}
                      </p>
                      {ad.classification_score !== undefined && (
                        <span className={`text-[10px] font-black ${ad.classification_score > 0 ? 'text-emerald-400' : ad.classification_score < 0 ? 'text-amber-400' : 'text-neutral-500'}`}>
                          {ad.classification_score > 0 ? `+${ad.classification_score}` : ad.classification_score}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3 flex flex-col justify-center">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                      <Layout size={10} className="text-blue-400" /> Page Type
                    </p>
                    <p className="text-xs font-bold text-white truncate px-1">
                      {ad.page_subtype || "General LP"}
                    </p>
                  </div>
                  <div className="bg-neutral-900/60 border border-white/5 rounded-xl p-3 flex flex-col justify-center">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                      <BrainCircuit size={10} className="text-purple-400" /> Features
                    </p>
                    <div className="flex gap-1">
                      {ad.has_video && <span className="text-[9px] bg-purple-500/20 text-purple-400 px-1 rounded" title="Video Sales Letter">VSL</span>}
                      {ad.has_countdown && <span className="text-[9px] bg-red-500/20 text-red-400 px-1 rounded" title="Countdown Timer">⏱</span>}
                      {ad.price_found && <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1 rounded">{ad.price_found}</span>}
                    </div>
                  </div>
                </div>

                {/* Screenshots Section */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <span className="text-[9px] font-black text-neutral-500 uppercase tracking-widest px-1">Landing Page</span>
                    <div className="aspect-[4/3] bg-black/40 rounded-xl overflow-hidden border border-white/5 group/ss cursor-zoom-in">
                       {ad.lp_screenshot_url ? (
                         <img 
                           src={ad.lp_screenshot_url} 
                           className="w-full h-full object-cover transition-transform group-hover/ss:scale-110" 
                           onClick={() => window.open(ad.lp_screenshot_url, '_blank')}
                         />
                       ) : (
                         <div className="w-full h-full flex items-center justify-center text-neutral-700 text-[10px] font-bold">NO SCREENSHOT</div>
                       )}
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <span className="text-[9px] font-black text-neutral-500 uppercase tracking-widest px-1">Offer Page</span>
                    <div className="aspect-[4/3] bg-black/40 rounded-xl overflow-hidden border border-white/5 group/ss cursor-zoom-in">
                        {ad.offer_screenshot_url ? (
                         <img 
                           src={ad.offer_screenshot_url} 
                           className="w-full h-full object-cover transition-transform group-hover/ss:scale-110" 
                           onClick={() => window.open(ad.offer_screenshot_url, '_blank')}
                         />
                       ) : (
                         <div className="w-full h-full flex items-center justify-center text-neutral-700 text-[10px] font-bold">OFFER HIDDEN</div>
                       )}
                    </div>
                  </div>

                {/* Forensic Signals */}
                {ad.analysis_params && ad.analysis_params.length > 0 && (
                  <div className="bg-neutral-900/60 border border-white/5 rounded-2xl p-4">
                    <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                      <Search size={12} className="text-primary" /> Forensic Evidence
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {ad.analysis_params.map((signal: string, i: number) => (
                        <span key={i} className={`px-2 py-1 rounded-md text-[9px] font-bold border ${
                          signal.includes('+') ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                          signal.includes('-') ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 
                          'bg-white/5 text-neutral-400 border-white/5'
                        }`}>
                          {signal}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
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

              </div>{/* end right column */}
            </div>{/* end grid */}
          </div>{/* end scrollable body */}

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
