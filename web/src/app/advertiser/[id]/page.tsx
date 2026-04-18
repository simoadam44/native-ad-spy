"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { 
  ChevronLeft, 
  Target, 
  Globe, 
  TrendingUp, 
  Layers, 
  Zap, 
  BarChart3,
  ExternalLink,
  ShieldCheck,
  MousePointer2
} from "lucide-react";
import { motion } from "framer-motion";

export default function AdvertiserProfilePage() {
  const params = useParams();
  const router = useRouter();
  const [profile, setProfile] = useState<any>(null);
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const affiliateId = params.id as string;

  useEffect(() => {
    async function fetchProfile() {
      setLoading(true);
      
      // 1. Fetch from View
      const { data: profileData } = await supabase
        .from("advertiser_profiles")
        .select("*")
        .eq("affiliate_id", affiliateId)
        .single();
      
      setProfile(profileData);

      // 2. Fetch Sample Ads
      const { data: adData } = await supabase
        .from("ads")
        .select("*")
        .eq("affiliate_id", affiliateId)
        .order("created_at", { ascending: false })
        .limit(12);
      
      setAds(adData || []);
      setLoading(false);
    }

    if (affiliateId) fetchProfile();
  }, [affiliateId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-primary"></div>
      </div>
    );
  }

  if (!profile && !loading) {
    return (
      <div className="p-10 text-center">
        <h2 className="text-xl font-bold">Advertiser Not Found</h2>
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
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Target size={28} />
              </div>
              <h1 className="text-4xl font-black font-syne tracking-tight">
                Advertiser: <span className="text-emerald-400">{affiliateId}</span>
              </h1>
            </div>
            <p className="text-neutral-500 font-medium max-w-2xl">
              Competitive analysis for affiliate partner discovered on {profile?.native_networks?.join(", ") || "Native Networks"}.
            </p>
          </div>

          <div className="bg-neutral-900/50 border border-white/5 rounded-2xl px-6 py-4 flex gap-8 backdrop-blur-xl">
             <div className="text-center">
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-1">Status</p>
                <div className="flex items-center gap-1.5 text-emerald-400 text-sm font-bold">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Active
                </div>
             </div>
             <div className="text-center">
                <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-1">First Seen</p>
                <p className="text-sm font-bold white">{new Date(profile?.first_seen).toLocaleDateString()}</p>
             </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Total Creatives", value: profile?.total_ads, icon: Layers, color: "text-blue-400" },
          { label: "Unique Offers", value: profile?.unique_offers, icon: Zap, color: "text-amber-400" },
          { label: "Estimated Reach", value: profile?.total_impressions.toLocaleString(), icon: TrendingUp, color: "text-emerald-400" },
          { label: "Niches", value: profile?.offer_vertical || "Multi-Vertical", icon: BarChart3, color: "text-purple-400" },
        ].map((stat, i) => (
          <div key={i} className="bg-card border border-border rounded-2xl p-6 space-y-3">
            <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center ${stat.color}`}>
              <stat.icon size={20} />
            </div>
            <div>
              <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{stat.label}</p>
              <p className="text-2xl font-black">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Analysis Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-black font-syne flex items-center gap-2">
            <BarChart3 className="text-primary" size={20} />
            Recent Advertising Portfolio
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {ads.map((ad) => (
              <div 
                key={ad.id} 
                className="bg-card border border-border rounded-2xl overflow-hidden group cursor-pointer hover:border-primary/50 transition-all"
                onClick={() => router.push(`/dashboard?ad=${ad.id}`)}
              >
                <div className="aspect-[16/10] relative overflow-hidden">
                  <img src={ad.image_url} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded text-[8px] font-black text-white uppercase">{ad.network}</div>
                </div>
                <div className="p-4 space-y-2">
                  <h4 className="text-xs font-bold line-clamp-1">{ad.title}</h4>
                  <div className="flex items-center justify-between text-[10px] text-neutral-500 font-bold uppercase tracking-tighter">
                    <span>{ad.offer_vertical}</span>
                    <span className="text-white">{ad.impressions?.toLocaleString()} Impressions</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-black font-syne flex items-center gap-2">
            <ShieldCheck className="text-emerald-400" size={20} />
            Tech Stack Fingerprint
          </h2>
          <div className="bg-card border border-border rounded-2xl p-6 space-y-6">
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                   <span className="text-xs text-neutral-400 font-medium">Preferred Tracker</span>
                   <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-[10px] font-black uppercase border border-blue-500/20">{profile?.tracker_tool || "Custom/None"}</span>
                </div>
                <div className="flex items-center justify-between">
                   <span className="text-xs text-neutral-400 font-medium">Primary Network</span>
                   <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-black uppercase border border-emerald-500/20">{profile?.affiliate_network || "Direct"}</span>
                </div>
                <div className="flex items-center justify-between">
                   <span className="text-xs text-neutral-400 font-medium">Target Geos</span>
                   <span className="text-xs text-white font-bold">{adData?.country_code || "Global"}</span>
                </div>
            </div>

            <div className="pt-6 border-t border-border">
              <p className="text-[10px] font-black text-neutral-500 uppercase tracking-widest mb-4">Traffic Sources</p>
              <div className="space-y-3">
                {profile?.native_networks?.map((net: string) => (
                  <div key={net} className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-[80%]" />
                    </div>
                    <span className="text-[10px] font-bold text-white uppercase w-16">{net}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
