"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { 
  ChevronLeft, 
  Package, 
  TrendingUp, 
  Users, 
  ExternalLink,
  ShieldCheck,
  MousePointer2,
  AlertTriangle,
  Globe2
} from "lucide-react";
import { motion } from "framer-motion";

export default function OfferIntelligencePage() {
  const params = useParams();
  const router = useRouter();
  const [offer, setOffer] = useState<any>(null);
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const offerId = params.id as string;

  useEffect(() => {
    async function fetchOfferData() {
      setLoading(true);
      
      // 1. Fetch from View
      const { data: offerData } = await supabase
        .from("offer_intelligence")
        .select("*")
        .eq("offer_id", offerId)
        .single();
      
      setOffer(offerData);

      // 2. Fetch Sample Creatives running this offer
      const { data: adData } = await supabase
        .from("ads")
        .select("*")
        .eq("offer_id", offerId)
        .order("impressions", { ascending: false })
        .limit(10);
      
      setAds(adData || []);
      setLoading(false);
    }

    if (offerId) fetchOfferData();
  }, [offerId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-primary"></div>
      </div>
    );
  }

  if (!offer && !loading) {
    return (
      <div className="p-10 text-center">
        <h2 className="text-xl font-bold font-syne">Offer Intelligence Not Found</h2>
        <p className="text-neutral-500 mt-2">ID: {offerId}</p>
        <button onClick={() => router.back()} className="mt-4 text-primary">Go Back</button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
      {/* Header */}
      <div className="flex flex-col gap-6">
        <button 
          onClick={() => router.back()}
          className="flex items-center gap-2 text-neutral-500 hover:text-white transition-all text-sm font-bold uppercase tracking-widest"
        >
          <ChevronLeft size={16} /> Back to Dashboard
        </button>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary">
                <Package size={28} />
              </div>
              <h1 className="text-4xl font-black font-syne tracking-tight">
                Offer: <span className="text-primary">{offerId}</span>
              </h1>
            </div>
            <div className="flex items-center gap-4 mt-2">
                 <div className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase tracking-widest text-neutral-400">
                    <ShieldCheck size={12} className="text-emerald-400" /> {offer?.affiliate_network || "Unknown Network"}
                 </div>
                 <div className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase tracking-widest text-neutral-400">
                    <Globe2 size={12} className="text-blue-400" /> {offer?.offer_vertical || "General"}
                 </div>
            </div>
          </div>

          <div className="bg-neutral-900/50 border border-white/5 rounded-2xl px-6 py-4 flex gap-8">
             <div className="text-center">
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-1">Domain</p>
                <div className="flex items-center gap-1.5 text-white text-sm font-bold truncate max-w-[200px]">
                  {offer?.offer_domain || "Hidden"}
                </div>
             </div>
             <div className="text-center">
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-1">Affiliates Running</p>
                <p className="text-sm font-bold text-emerald-400">{offer?.total_affiliates || 1}</p>
             </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Active Creatives", value: offer?.total_ads, icon: Package, color: "text-blue-400" },
          { label: "Viral Heat", value: offer?.total_impressions.toLocaleString(), icon: TrendingUp, color: "text-red-400" },
          { label: "Traffic Sources", value: offer?.native_networks?.length || 1, icon: Globe2, color: "text-emerald-400" },
        ].map((stat, i) => (
          <div key={i} className="bg-card border border-border rounded-2xl p-6 flex items-center gap-5">
            <div className={`w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center ${stat.color}`}>
              <stat.icon size={24} />
            </div>
            <div>
              <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{stat.label}</p>
              <p className="text-2xl font-black">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 space-y-8">
          <section className="space-y-4">
             <h3 className="text-xl font-black font-syne">Top Performing Creatives</h3>
             <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {ads.map(ad => (
                  <div key={ad.id} className="bg-card border border-border rounded-2xl overflow-hidden hover:border-primary transition-all cursor-pointer" onClick={() => router.push(`/dashboard?ad=${ad.id}`)}>
                    <img src={ad.image_url} className="aspect-video object-cover w-full" />
                    <div className="p-4 space-y-2">
                        <p className="text-[10px] font-bold text-neutral-500 truncate">{ad.title}</p>
                        <div className="flex items-center justify-between">
                            <span className="text-[9px] font-black text-primary uppercase">{ad.network}</span>
                            <span className="text-[9px] font-bold text-white uppercase">{ad.impressions?.toLocaleString()} Impressions</span>
                        </div>
                    </div>
                  </div>
                ))}
             </div>
          </section>
        </div>

        <div className="space-y-8">
            <section className="bg-card border border-border rounded-2xl p-6 space-y-6">
                <h4 className="text-xs font-black uppercase tracking-widest text-neutral-400 border-b border-border pb-3">Forensic Pulse</h4>
                
                <div className="space-y-4">
                    <div className="space-y-1">
                        <p className="text-[9px] font-black text-neutral-500 uppercase tracking-tighter">Trackers Detected</p>
                        <div className="flex flex-wrap gap-2">
                            {offer?.trackers_used?.map((t: string) => (
                                <span key={t} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-md text-[9px] font-black border border-blue-500/20">{t}</span>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-1">
                        <p className="text-[9px] font-black text-neutral-500 uppercase tracking-tighter">Native Distribution</p>
                        <div className="flex flex-wrap gap-2">
                            {offer?.native_networks?.map((n: string) => (
                                <span key={n} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-md text-[9px] font-black border border-emerald-500/20">{n}</span>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 space-y-2">
                    <div className="flex items-center gap-2 text-amber-500">
                        <AlertTriangle size={14} />
                        <span className="text-[10px] font-black uppercase">Competitive Alert</span>
                    </div>
                    <p className="text-[10px] text-amber-200/70 font-medium leading-relaxed">
                        This offer is currently being scaled by {offer?.total_affiliates} high-volume partners across multiple native networks.
                    </p>
                </div>
            </section>
        </div>
      </div>
    </div>
  );
}
