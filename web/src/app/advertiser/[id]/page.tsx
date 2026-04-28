"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  ChevronLeft, Target, Globe, TrendingUp, Layers, Zap,
  BarChart3, ShieldCheck, ExternalLink, Copy, Calendar,
  Activity, Network, MousePointer2, Award
} from "lucide-react";
import { motion } from "framer-motion";

export default function AdvertiserProfilePage() {
  const params = useParams();
  const router = useRouter();
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const affiliateId = params.id as string;

  useEffect(() => {
    async function fetchAds() {
      setLoading(true);
      // Query ads table directly — no view needed
      const { data } = await supabase
        .from("ads")
        .select("*")
        .eq("affiliate_id", affiliateId)
        .order("created_at", { ascending: false })
        .limit(50);
      setAds(data || []);
      setLoading(false);
    }
    if (affiliateId) fetchAds();
  }, [affiliateId]);

  // Derive all stats from raw ads data
  const stats = useMemo(() => {
    if (!ads.length) return null;
    const networks = [...new Set(ads.map(a => a.network).filter(Boolean))];
    const offers = [...new Set(ads.map(a => a.offer_domain || a.final_offer_url).filter(Boolean))];
    const geos = [...new Set(ads.map(a => a.country_code).filter(Boolean))];
    const verticals = [...new Set(ads.map(a => a.offer_vertical).filter(Boolean))];
    const trackers = [...new Set(ads.map(a => a.tracker_tool).filter(Boolean))];
    const affiliateNet = ads.find(a => a.affiliate_network)?.affiliate_network || "Direct/In-house";
    const totalImpressions = ads.reduce((s, a) => s + (a.impressions || 1), 0);
    const firstSeen = ads.reduce((min, a) => (!min || a.created_at < min) ? a.created_at : min, null);
    const lastSeen = ads.reduce((max, a) => (!max || a.created_at > max) ? a.created_at : max, null);

    // Network distribution count
    const netCounts: Record<string, number> = {};
    ads.forEach(a => { if (a.network) netCounts[a.network] = (netCounts[a.network] || 0) + 1; });
    const maxNetCount = Math.max(...Object.values(netCounts));

    return { networks, offers, geos, verticals, trackers, affiliateNet, totalImpressions, firstSeen, lastSeen, netCounts, maxNetCount };
  }, [ads]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="space-y-4 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary mx-auto" />
          <p className="text-neutral-500 text-sm font-bold uppercase tracking-widest">Loading Advertiser Intelligence...</p>
        </div>
      </div>
    );
  }

  if (!ads.length && !loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] space-y-4">
        <div className="w-20 h-20 rounded-3xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
          <Target size={36} className="text-red-400" />
        </div>
        <h2 className="text-2xl font-black font-syne">Advertiser Not Found</h2>
        <p className="text-neutral-500 text-sm">No ads found for Affiliate ID: <code className="text-primary font-mono">{affiliateId}</code></p>
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
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-transparent to-transparent" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Target size={28} />
              </div>
              <div>
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">Affiliate Partner</p>
                <h1 className="text-3xl font-black font-syne tracking-tight flex items-center gap-2">
                  ID: <span className="text-emerald-400">{affiliateId}</span>
                  <button onClick={() => navigator.clipboard.writeText(affiliateId)} className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-500 hover:text-white transition-all">
                    <Copy size={14} />
                  </button>
                </h1>
              </div>
            </div>
            <p className="text-neutral-400 text-sm font-medium">
              Running on <span className="text-white font-bold">{stats?.networks.join(", ") || "Unknown"}</span>
              {stats?.affiliateNet && <> · Network: <span className="text-emerald-400 font-bold">{stats.affiliateNet}</span></>}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4 shrink-0">
            {[
              { label: "First Seen", value: stats?.firstSeen ? new Date(stats.firstSeen).toLocaleDateString() : "—", icon: Calendar },
              { label: "Last Active", value: stats?.lastSeen ? new Date(stats.lastSeen).toLocaleDateString() : "—", icon: Activity },
              { label: "Status", value: "Active", icon: Award, green: true },
            ].map((s, i) => (
              <div key={i} className="bg-black/30 border border-white/5 rounded-2xl px-4 py-3 text-center">
                <s.icon size={14} className={`mx-auto mb-1 ${s.green ? "text-emerald-400" : "text-neutral-500"}`} />
                <p className="text-[9px] font-black text-neutral-500 uppercase tracking-widest">{s.label}</p>
                <p className={`text-sm font-bold mt-0.5 ${s.green ? "text-emerald-400" : ""}`}>{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Creatives", value: ads.length, icon: Layers, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
          { label: "Unique Offers", value: stats?.offers.length || 0, icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
          { label: "Total Impressions", value: (stats?.totalImpressions || 0).toLocaleString(), icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
          { label: "Geos Targeted", value: stats?.geos.length || 0, icon: Globe, color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
        ].map((stat, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }} className="bg-card border border-border rounded-2xl p-6 space-y-3 hover:border-white/10 transition-all">
            <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${stat.bg} ${stat.color}`}>
              <stat.icon size={20} />
            </div>
            <div>
              <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{stat.label}</p>
              <p className="text-2xl font-black mt-0.5">{stat.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Creatives Grid */}
        <div className="lg:col-span-2 space-y-5">
          <h2 className="text-lg font-black font-syne flex items-center gap-2 uppercase tracking-tight">
            <BarChart3 className="text-primary" size={20} /> Advertising Portfolio ({ads.length} creatives)
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {ads.slice(0, 12).map((ad, i) => (
              <motion.div
                key={ad.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                className="bg-card border border-border rounded-2xl overflow-hidden group cursor-pointer hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all"
                onClick={() => router.push(`/dashboard?ad=${ad.id}`)}
              >
                <div className="aspect-[4/3] relative overflow-hidden bg-neutral-900">
                  {ad.image_url
                    ? <img src={ad.image_url} alt={ad.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    : <div className="w-full h-full flex items-center justify-center text-neutral-700"><Layers size={28} /></div>
                  }
                  <div className="absolute top-2 left-2 flex gap-1">
                    <span className="bg-black/70 backdrop-blur px-1.5 py-0.5 rounded text-[8px] font-black text-white uppercase">{ad.network}</span>
                    {ad.country_code && <span className="bg-black/70 backdrop-blur px-1.5 py-0.5 rounded text-[8px] font-black text-neutral-300">{ad.country_code}</span>}
                  </div>
                </div>
                <div className="p-3 space-y-1.5">
                  <p className="text-xs font-bold line-clamp-2 leading-tight">{ad.title}</p>
                  <div className="flex items-center justify-between">
                    {ad.ad_type && (
                      <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded ${ad.ad_type === "Affiliate" ? "bg-emerald-500/15 text-emerald-400" : "bg-blue-500/15 text-blue-400"}`}>
                        {ad.ad_type}
                      </span>
                    )}
                    <span className="text-[9px] text-neutral-500 font-bold">{(ad.impressions || 1).toLocaleString()} impr.</span>
                  </div>
                  {ad.offer_domain && (
                    <p className="text-[9px] text-neutral-600 font-mono truncate">{ad.offer_domain}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Sidebar Intelligence */}
        <div className="space-y-5">

          {/* Tech Stack */}
          <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <h3 className="text-xs font-black uppercase tracking-widest text-neutral-400 flex items-center gap-2">
              <ShieldCheck size={14} className="text-emerald-400" /> Tech Stack Fingerprint
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-400 font-medium">Affiliate Network</span>
                <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-black uppercase border border-emerald-500/20 max-w-[120px] truncate">{stats?.affiliateNet}</span>
              </div>
              {stats?.trackers[0] && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-neutral-400 font-medium">Tracker</span>
                  <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-[10px] font-black uppercase border border-blue-500/20">{stats.trackers[0]}</span>
                </div>
              )}
              {stats?.verticals[0] && (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-neutral-400 font-medium">Vertical</span>
                  <span className="px-2 py-1 bg-purple-500/10 text-purple-400 rounded text-[10px] font-black uppercase border border-purple-500/20">{stats.verticals[0]}</span>
                </div>
              )}
            </div>
          </div>

          {/* Network Breakdown */}
          <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-neutral-400 flex items-center gap-2">
              <Network size={14} className="text-primary" /> Traffic Source Distribution
            </h3>
            <div className="space-y-3">
              {Object.entries(stats?.netCounts || {}).sort((a, b) => b[1] - a[1]).map(([net, count]) => (
                <div key={net} className="space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-white">{net}</span>
                    <span className="text-[10px] text-neutral-500 font-bold">{count} ads</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.round((count / ads.length) * 100)}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className="h-full bg-primary rounded-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Offer Domains */}
          {stats && stats.offers.length > 0 && (
            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-neutral-400 flex items-center gap-2">
                <ExternalLink size={14} className="text-amber-400" /> Promoted Offer Domains
              </h3>
              <div className="space-y-2">
                {stats.offers.slice(0, 5).map((offer, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 bg-white/3 rounded-xl border border-white/5 group hover:border-amber-500/20 transition-all">
                    <div className="w-6 h-6 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                      <Globe size={12} className="text-amber-400" />
                    </div>
                    <span className="text-xs font-mono text-neutral-300 truncate group-hover:text-white transition-colors">{offer}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Geos */}
          {stats && stats.geos.length > 0 && (
            <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-neutral-400 flex items-center gap-2">
                <Globe size={14} className="text-purple-400" /> Target Geos
              </h3>
              <div className="flex flex-wrap gap-2">
                {stats.geos.map((geo) => (
                  <span key={geo} className="px-2.5 py-1 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white">{geo}</span>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
