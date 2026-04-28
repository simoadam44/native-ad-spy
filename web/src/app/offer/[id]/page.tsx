"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  ChevronLeft, Package, TrendingUp, Globe2, ShieldCheck,
  AlertTriangle, ExternalLink, Copy, Link2, ArrowRight,
  MousePointer2, Activity, Layers, Network, Eye
} from "lucide-react";
import { motion } from "framer-motion";

export default function OfferIntelligencePage() {
  const params = useParams();
  const router = useRouter();
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const offerId = params.id as string;

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      // Query ads table directly by offer_id OR by final_offer_url containing the id
      const { data } = await supabase
        .from("ads")
        .select("*")
        .eq("offer_id", offerId)
        .order("impressions", { ascending: false })
        .limit(30);

      // If nothing found by offer_id, try by offer_domain
      if (!data?.length) {
        const { data: byDomain } = await supabase
          .from("ads")
          .select("*")
          .ilike("final_offer_url", `%${offerId}%`)
          .order("impressions", { ascending: false })
          .limit(30);
        setAds(byDomain || []);
      } else {
        setAds(data);
      }
      setLoading(false);
    }
    if (offerId) fetchData();
  }, [offerId]);

  // Derive all stats from raw ads
  const stats = useMemo(() => {
    if (!ads.length) return null;
    const networks = [...new Set(ads.map(a => a.network).filter(Boolean))];
    const affiliates = [...new Set(ads.map(a => a.affiliate_id).filter(Boolean))];
    const geos = [...new Set(ads.map(a => a.country_code).filter(Boolean))];
    const trackers = [...new Set(ads.map(a => a.tracker_tool).filter(Boolean))];
    const affiliateNet = ads.find(a => a.affiliate_network)?.affiliate_network || "Direct/In-house";
    const vertical = ads.find(a => a.offer_vertical)?.offer_vertical || "General";
    const totalImpressions = ads.reduce((s, a) => s + (a.impressions || 1), 0);
    const offerDomain = ads.find(a => a.offer_domain)?.offer_domain;
    const finalOfferUrl = ads.find(a => a.final_offer_url)?.final_offer_url;
    const landingUrl = ads.find(a => a.landing)?.landing;
    const firstSeen = ads.reduce((min, a) => (!min || a.created_at < min) ? a.created_at : min, null);
    const lastSeen = ads.reduce((max, a) => (!max || a.created_at > max) ? a.created_at : max, null);
    const redirectChains = ads
      .filter(a => a.redirect_chain && Array.isArray(a.redirect_chain))
      .flatMap(a => a.redirect_chain)
      .filter(Boolean);

    // Network distribution
    const netCounts: Record<string, number> = {};
    ads.forEach(a => { if (a.network) netCounts[a.network] = (netCounts[a.network] || 0) + 1; });

    return { networks, affiliates, geos, trackers, affiliateNet, vertical, totalImpressions, offerDomain, finalOfferUrl, landingUrl, firstSeen, lastSeen, redirectChains, netCounts };
  }, [ads]);

  const copyText = (text: string) => navigator.clipboard.writeText(text);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="space-y-4 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary mx-auto" />
          <p className="text-neutral-500 text-sm font-bold uppercase tracking-widest">Loading Offer Intelligence...</p>
        </div>
      </div>
    );
  }

  if (!ads.length && !loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-4">
        <div className="w-20 h-20 rounded-3xl bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Package size={36} className="text-primary" />
        </div>
        <h2 className="text-2xl font-black font-syne">Offer Not Found</h2>
        <p className="text-neutral-500 text-sm">No ads found for Offer ID: <code className="text-primary font-mono">{offerId}</code></p>
        <button onClick={() => router.back()} className="mt-2 bg-primary/10 hover:bg-primary text-primary hover:text-white border border-primary/30 px-6 py-2.5 rounded-xl text-sm font-bold transition-all">
          ← Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">

      {/* Back */}
      <button onClick={() => router.back()} className="flex items-center gap-2 text-neutral-500 hover:text-white transition-all text-xs font-black uppercase tracking-widest">
        <ChevronLeft size={16} /> Back to Dashboard
      </button>

      {/* Hero Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-3xl p-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="space-y-4 flex-1">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
                <Package size={28} />
              </div>
              <div>
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">Offer Intelligence</p>
                <h1 className="text-2xl font-black font-syne tracking-tight flex items-center gap-2">
                  Offer ID: <span className="text-primary">{offerId}</span>
                  <button onClick={() => copyText(offerId)} className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-500 hover:text-white transition-all">
                    <Copy size={13} />
                  </button>
                </h1>
              </div>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-2">
              <span className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase text-neutral-400">
                <ShieldCheck size={11} className="text-emerald-400" /> {stats?.affiliateNet}
              </span>
              <span className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase text-neutral-400">
                <Globe2 size={11} className="text-blue-400" /> {stats?.vertical}
              </span>
              {stats?.trackers[0] && (
                <span className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase text-neutral-400">
                  <Activity size={11} className="text-amber-400" /> {stats.trackers[0]}
                </span>
              )}
            </div>

            {/* Offer URL */}
            {stats?.finalOfferUrl && (
              <div className="bg-black/40 border border-emerald-500/20 rounded-2xl p-4 space-y-2">
                <p className="text-[9px] font-black text-emerald-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Link2 size={10} /> Final Offer URL
                </p>
                <div className="flex items-center gap-3">
                  <code className="text-xs text-white font-mono flex-1 truncate">{stats.finalOfferUrl}</code>
                  <div className="flex gap-1.5 shrink-0">
                    <button onClick={() => copyText(stats.finalOfferUrl!)} className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-400 hover:text-white transition-all" title="Copy">
                      <Copy size={13} />
                    </button>
                    <a href={stats.finalOfferUrl} target="_blank" rel="noopener noreferrer" className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-400 hover:text-emerald-400 transition-all" title="Open">
                      <ExternalLink size={13} />
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* Landing URL */}
            {stats?.landingUrl && (
              <div className="bg-black/40 border border-blue-500/20 rounded-2xl p-4 space-y-2">
                <p className="text-[9px] font-black text-blue-400 uppercase tracking-widest flex items-center gap-1.5">
                  <MousePointer2 size={10} /> Landing Page URL
                </p>
                <div className="flex items-center gap-3">
                  <code className="text-xs text-white font-mono flex-1 truncate">{stats.landingUrl}</code>
                  <div className="flex gap-1.5 shrink-0">
                    <button onClick={() => copyText(stats.landingUrl!)} className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-400 hover:text-white transition-all" title="Copy">
                      <Copy size={13} />
                    </button>
                    <a href={stats.landingUrl} target="_blank" rel="noopener noreferrer" className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-400 hover:text-blue-400 transition-all" title="Open">
                      <ExternalLink size={13} />
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Quick Stats Panel */}
          <div className="grid grid-cols-2 gap-3 shrink-0 min-w-[220px]">
            {[
              { label: "Domain", value: stats?.offerDomain || "Hidden", icon: Globe2 },
              { label: "Affiliates Running", value: stats?.affiliates.length || 1, icon: Network },
              { label: "First Seen", value: stats?.firstSeen ? new Date(stats.firstSeen).toLocaleDateString() : "—", icon: Activity },
              { label: "Last Active", value: stats?.lastSeen ? new Date(stats.lastSeen).toLocaleDateString() : "—", icon: Eye },
            ].map((s, i) => (
              <div key={i} className="bg-black/40 border border-white/5 rounded-2xl px-3 py-3">
                <s.icon size={13} className="text-neutral-500 mb-1" />
                <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">{s.label}</p>
                <p className="text-sm font-bold text-white mt-0.5 truncate">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Active Creatives", value: ads.length, icon: Package, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
          { label: "Total Impressions", value: (stats?.totalImpressions || 0).toLocaleString(), icon: TrendingUp, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
          { label: "Traffic Sources", value: stats?.networks.length || 1, icon: Globe2, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
        ].map((stat, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="bg-card border border-border rounded-2xl p-6 flex items-center gap-5 hover:border-white/10 transition-all">
            <div className={`w-12 h-12 rounded-xl border flex items-center justify-center ${stat.bg} ${stat.color}`}>
              <stat.icon size={24} />
            </div>
            <div>
              <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{stat.label}</p>
              <p className="text-2xl font-black">{stat.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

        {/* Creatives */}
        <div className="lg:col-span-3 space-y-5">
          <h2 className="text-lg font-black font-syne flex items-center gap-2 uppercase tracking-tight">
            <Layers className="text-primary" size={20} /> Top Performing Creatives
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {ads.map((ad, i) => (
              <motion.div
                key={ad.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                className="bg-card border border-border rounded-2xl overflow-hidden group cursor-pointer hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all"
                onClick={() => router.push(`/dashboard?ad=${ad.id}`)}
              >
                <div className="aspect-video relative overflow-hidden bg-neutral-900">
                  {ad.image_url
                    ? <img src={ad.image_url} alt={ad.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    : <div className="w-full h-full flex items-center justify-center text-neutral-700"><Package size={24} /></div>
                  }
                  <div className="absolute top-2 left-2 flex gap-1">
                    <span className="bg-black/70 backdrop-blur px-1.5 py-0.5 rounded text-[8px] font-black text-white uppercase">{ad.network}</span>
                  </div>
                </div>
                <div className="p-3 space-y-1.5">
                  <p className="text-xs font-bold line-clamp-2 leading-tight">{ad.title}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-primary uppercase">{ad.network}</span>
                    <span className="text-[9px] font-bold text-neutral-500">{(ad.impressions || 1).toLocaleString()} impr.</span>
                  </div>
                  {ad.affiliate_id && (
                    <p className="text-[9px] text-neutral-600 font-mono">aff: {ad.affiliate_id}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-5">

          {/* Forensic Pulse */}
          <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <h4 className="text-xs font-black uppercase tracking-widest text-neutral-400 border-b border-border pb-3 flex items-center gap-2">
              <ShieldCheck size={13} className="text-emerald-400" /> Forensic Pulse
            </h4>
            <div className="space-y-4">
              {stats?.trackers.length ? (
                <div className="space-y-2">
                  <p className="text-[9px] font-black text-neutral-500 uppercase tracking-tighter">Trackers Detected</p>
                  <div className="flex flex-wrap gap-1.5">
                    {stats.trackers.map(t => (
                      <span key={t} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-md text-[9px] font-black border border-blue-500/20">{t}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="space-y-2">
                <p className="text-[9px] font-black text-neutral-500 uppercase tracking-tighter">Native Distribution</p>
                <div className="flex flex-wrap gap-1.5">
                  {stats?.networks.map(n => (
                    <span key={n} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-md text-[9px] font-black border border-emerald-500/20">{n}</span>
                  ))}
                </div>
              </div>
              {stats && stats.geos.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[9px] font-black text-neutral-500 uppercase tracking-tighter">Geo Targeting</p>
                  <div className="flex flex-wrap gap-1.5">
                    {stats.geos.map(g => (
                      <span key={g} className="px-2 py-0.5 bg-white/5 text-white rounded-md text-[9px] font-bold border border-white/10">{g}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Affiliates Running */}
          {stats && stats.affiliates.length > 0 && (
            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
              <h4 className="text-xs font-black uppercase tracking-widest text-neutral-400 flex items-center gap-2">
                <Network size={13} className="text-purple-400" /> Affiliates Running This Offer
              </h4>
              <div className="space-y-2">
                {stats.affiliates.slice(0, 8).map((aff, i) => (
                  <button
                    key={i}
                    onClick={() => router.push(`/advertiser/${aff}`)}
                    className="w-full flex items-center justify-between p-2.5 bg-white/3 hover:bg-white/5 border border-white/5 hover:border-purple-500/30 rounded-xl transition-all group"
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-purple-500/10 flex items-center justify-center text-[9px] font-black text-purple-400">{String(i + 1).padStart(2, "0")}</div>
                      <span className="text-xs font-mono text-white">{aff}</span>
                    </div>
                    <ArrowRight size={12} className="text-neutral-600 group-hover:text-white transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Competitive Alert */}
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-amber-500">
              <AlertTriangle size={14} />
              <span className="text-[10px] font-black uppercase tracking-widest">Competitive Alert</span>
            </div>
            <p className="text-[10px] text-amber-200/70 font-medium leading-relaxed">
              This offer is currently being scaled by <strong className="text-amber-400">{stats?.affiliates.length || 1}</strong> high-volume partners across multiple native networks.
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}
