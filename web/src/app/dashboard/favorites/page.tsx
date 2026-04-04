"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { Heart, Globe, Flame, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";

export default function FavoritesPage() {
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFavorites() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data: favs } = await supabase.from("favorites").select("ad_id").eq("user_id", user.id);
      const adIds = favs?.map(f => f.ad_id) || [];
      
      if (adIds.length > 0) {
        const { data: adData } = await supabase.from("ads").select("*").in("id", adIds);
        setAds(adData || []);
      }
      setLoading(false);
    }
    loadFavorites();
  }, []);

  if (loading) return <div className="text-neutral-500 font-bold uppercase tracking-widest animate-pulse">Loading Gems...</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-4xl font-bold font-syne uppercase">My Saved Gems</h1>
      
      {ads.length === 0 ? (
        <div className="bg-card border border-border rounded-3xl p-20 text-center flex flex-col items-center gap-4">
           <Heart className="text-neutral-800" size={64} />
           <p className="text-neutral-500 font-bold tracking-widest uppercase">Your collection is empty</p>
           <a href="/dashboard" className="text-primary text-sm font-bold hover:underline">Go discover some ads</a>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {ads.map((ad) => (
            <motion.div 
              key={ad.id}
              className="bg-card border border-border rounded-2xl overflow-hidden group hover:border-primary/40 transition-all flex flex-col"
            >
              <div className="relative h-48 overflow-hidden">
                <img 
                  src={ad.image || "https://images.unsplash.com/photo-1611162617474-5b21e879e113?q=80&w=400"} 
                  className="w-full h-full object-cover"
                  alt={ad.title}
                />
              </div>
              <div className="p-5 flex flex-col flex-1">
                <h3 className="text-sm font-bold line-clamp-2">{ad.title}</h3>
                <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
                   <span className="text-xs font-bold text-primary uppercase">{ad.network}</span>
                   <a href={ad.landing} target="_blank" className="p-2 hover:bg-neutral-800 rounded-lg transition-all text-neutral-400 hover:text-white">
                      <ExternalLink size={16} />
                   </a>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
