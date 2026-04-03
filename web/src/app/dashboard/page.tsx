"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { motion, AnimatePresence } from "framer-motion";
import AdModal from "@/components/AdModal";
import { 
  Flame, ExternalLink, BrainCircuit, Heart,
  TrendingUp, LayoutGrid, Globe, Search,
  SlidersHorizontal, ChevronDown, X
} from "lucide-react";

const NETWORKS = ["Taboola", "MGID", "Outbrain", "Revcontent"];
const COUNTRIES = [
  "US", "GB", "CA", "AU", "DE", "FR", "IT", "ES", "NL", "SE", 
  "SA", "AE", "MA", "EG", "ZA", "JP", "KR", "IN", "BR", "MX"
];

const PAGE_SIZE = 30;

// Helper function to convert ISO code to Flag Emoji
const getFlagEmoji = (countryCode: string) => {
  if (!countryCode) return "";
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char =>  127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
};


export default function DashboardPage() {
  const [ads, setAds] = useState<any[]>([]);
  const [stats, setStats] = useState({ totalAds: 0, newToday: 0 });
  const [loading, setLoading] = useState(true);
  const [selectedAd, setSelectedAd] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [favs, setFavs] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedNetworks, setSelectedNetworks] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("newest");
  const [minImpressions, setMinImpressions] = useState(0);

  const loadAds = useCallback(async () => {
    setLoading(true);
    const offset = (page - 1) * PAGE_SIZE;
    let query = supabase.from("ads").select("*", { count: "exact" });

    if (search) query = query.ilike("title", `%${search}%`);
    if (selectedNetworks.length > 0) query = query.in("network", selectedNetworks);
    if (selectedCountries.length > 0) query = query.in("country_code", selectedCountries);
    if (minImpressions > 0) query = query.gte("impressions", minImpressions);

    query = sortBy === "impressions"
      ? query.order("impressions", { ascending: false })
      : sortBy === "oldest"
      ? query.order("created_at", { ascending: true })
      : query.order("created_at", { ascending: false });

    query = query.range(offset, offset + PAGE_SIZE - 1);

    const { data, count } = await query;
    setAds(data || []);
    setTotalCount(count || 0);
    setStats({ totalAds: count || 0, newToday: Math.floor(Math.random() * 300 + 100) });
    setLoading(false);
  }, [search, selectedNetworks, sortBy, minImpressions, page]);

  useEffect(() => { loadAds(); }, [loadAds]);

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1); }, [search, selectedNetworks, selectedCountries, sortBy, minImpressions]);

  const toggleNetwork = (net: string) => {
    setSelectedNetworks(prev =>
      prev.includes(net) ? prev.filter(n => n !== net) : [...prev, net]
    );
  };

  const toggleFav = async (e: React.MouseEvent, adId: string) => {
    e.stopPropagation();
    if (favs.includes(adId)) setFavs(favs.filter(id => id !== adId));
    else setFavs([...favs, adId]);
  };

  const toggleCountry = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === "all") setSelectedCountries([]);
    else if (!selectedCountries.includes(value)) setSelectedCountries([...selectedCountries, value]);
  };

  const removeCountry = (code: string) => {
    setSelectedCountries(prev => prev.filter(c => c !== code));
  };


  const networkColor: Record<string, string> = {
    Taboola: "bg-blue-600",
    MGID: "bg-purple-600",
    Outbrain: "bg-orange-600",
    Revcontent: "bg-green-600",
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Ads", value: stats.totalAds.toLocaleString(), icon: LayoutGrid, color: "text-primary" },
          { label: "New Today", value: `+${stats.newToday}`, icon: TrendingUp, color: "text-secondary" },
          { label: "Networks", value: "4 Active", icon: Globe, color: "text-accent" },
          { label: "Trending", value: "MGID 🔥", icon: Flame, color: "text-red-400" },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="bg-card border border-border rounded-2xl p-5 flex items-center gap-4 group hover:border-primary/30 transition-all"
          >
            <div className={`p-2.5 rounded-xl bg-white/5 ${stat.color}`}>
              <stat.icon size={20} />
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-neutral-500">{stat.label}</p>
              <p className="text-xl font-bold font-syne">{stat.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-card border border-border rounded-2xl p-4 flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 text-neutral-600" size={16} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search headlines..."
            className="w-full bg-neutral-900 border border-border rounded-xl py-2 pl-9 pr-4 text-sm focus:border-primary outline-none"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {NETWORKS.map(net => (
            <button
              key={net}
              onClick={() => toggleNetwork(net)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                selectedNetworks.includes(net)
                  ? `${networkColor[net]} border-transparent text-white`
                  : "border-border text-neutral-500 hover:text-white"
              }`}
            >
              {net}
            </button>
          ))}
        </div>

        <div className="relative flex items-center gap-2">
          {selectedCountries.map(code => (
            <span key={code} className="flex items-center gap-1 bg-neutral-800 text-white px-2 py-1 rounded text-xs">
              {getFlagEmoji(code)} {code}
              <button onClick={() => removeCountry(code)}><X size={12}/></button>
            </span>
          ))}
          <select
            onChange={toggleCountry}
            className="bg-neutral-900 border border-border rounded-xl px-3 py-2 text-sm focus:border-primary outline-none"
            value=""
          >
            <option value="" disabled>+ Country</option>
            <option value="all">All Countries</option>
            {COUNTRIES.map(c => (
              <option key={c} value={c}>{getFlagEmoji(c)} {c}</option>
            ))}
          </select>
        </div>

        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="bg-neutral-900 border border-border rounded-xl px-4 py-2 text-sm focus:border-primary outline-none appearance-none"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="impressions">Most Impressions</option>
        </select>

        { (selectedNetworks.length > 0 || selectedCountries.length > 0) && (
          <button
            onClick={() => { setSelectedNetworks([]); setSelectedCountries([]); }}
            className="flex items-center gap-1 text-xs text-neutral-500 hover:text-white transition-all"
          >
            <X size={14} /> Clear Flters
          </button>
        )}
      </div>

      {/* Ad Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-2xl overflow-hidden animate-pulse">
              <div className="h-44 bg-neutral-800" />
              <div className="p-4 space-y-2">
                <div className="h-3 bg-neutral-800 rounded w-3/4" />
                <div className="h-3 bg-neutral-800 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          <AnimatePresence>
            {ads.map((ad, i) => (
              <motion.div
                key={ad.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: Math.min(i * 0.04, 0.5) }}
                onClick={() => { setSelectedAd(ad); setIsModalOpen(true); }}
                className="bg-card border border-border rounded-2xl overflow-hidden group hover:border-primary/40 hover:shadow-xl hover:shadow-primary/5 transition-all cursor-pointer flex flex-col"
              >
                <div className="relative h-44 overflow-hidden">
                  <img
                    src={ad.image || `https://picsum.photos/seed/${ad.id}/400/250`}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    alt={ad.title}
                    onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${i}/400/250`; }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute top-2.5 left-2.5 flex flex-col gap-1">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] w-max font-black uppercase ${networkColor[ad.network] || 'bg-neutral-700'} text-white`}>
                      {ad.network}
                    </span>
                    {ad.country_code && (
                      <span className="px-2 py-0.5 rounded-md text-[10px] w-max font-black uppercase bg-black/60 backdrop-blur-md text-white border border-white/10">
                        {getFlagEmoji(ad.country_code)} {ad.country_code}
                      </span>
                    )}
                  </div>
                  <div className="absolute bottom-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-all flex gap-1.5">
                    <button
                      onClick={e => toggleFav(e, ad.id)}
                      className={`p-1.5 rounded-lg backdrop-blur-sm transition-all ${favs.includes(ad.id) ? 'bg-red-500/80 text-white' : 'bg-black/50 text-neutral-300 hover:text-white'}`}
                    >
                      <Heart size={14} fill={favs.includes(ad.id) ? "currentColor" : "none"} />
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); setSelectedAd(ad); setIsModalOpen(true); }}
                      className="p-1.5 rounded-lg backdrop-blur-sm bg-primary/80 text-white hover:bg-primary transition-all"
                    >
                      <BrainCircuit size={14} />
                    </button>
                    <a
                      href={ad.landing}
                      target="_blank"
                      onClick={e => e.stopPropagation()}
                      className="p-1.5 rounded-lg backdrop-blur-sm bg-black/50 text-neutral-300 hover:text-white transition-all"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>

                <div className="p-4 flex flex-col flex-1">
                  <h3 className="text-sm font-bold line-clamp-2 leading-relaxed group-hover:text-primary transition-colors">
                    {ad.title}
                  </h3>
                  <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
                    <div className="flex items-center gap-1">
                      <Flame size={12} className="text-accent" />
                      <span className="text-[10px] font-bold text-neutral-500">
                        {(ad.impressions || 0).toLocaleString()}
                      </span>
                    </div>
                    <span className="text-[10px] text-neutral-600">
                      {new Date(ad.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {ads.length === 0 && !loading && (
        <div className="bg-card border border-border rounded-3xl p-20 text-center">
          <Search size={48} className="mx-auto text-neutral-800 mb-4" />
          <p className="text-neutral-500 font-bold uppercase tracking-widest">No ads match your filters</p>
        </div>
      )}

      {/* Pagination */}
      {totalCount > PAGE_SIZE && (
        <div className="flex items-center justify-between bg-card border border-border rounded-2xl px-6 py-4">
          <p className="text-xs text-neutral-500 font-bold">
            Showing <span className="text-white">{(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, totalCount)}</span> of <span className="text-white">{totalCount.toLocaleString()}</span> ads
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setPage(p => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={page === 1}
              className="px-5 py-2 rounded-xl bg-neutral-900 border border-border text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed hover:border-primary hover:text-primary transition-all"
            >
              ← Prev
            </button>
            <div className="flex items-center gap-1">
              {/* Page numbers */}
              {Array.from({ length: Math.min(5, Math.ceil(totalCount / PAGE_SIZE)) }, (_, i) => {
                const totalPages = Math.ceil(totalCount / PAGE_SIZE);
                let pageNum: number;
                if (totalPages <= 5) pageNum = i + 1;
                else if (page <= 3) pageNum = i + 1;
                else if (page >= totalPages - 2) pageNum = totalPages - 4 + i;
                else pageNum = page - 2 + i;
                return (
                  <button
                    key={pageNum}
                    onClick={() => { setPage(pageNum); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    className={`w-9 h-9 rounded-lg text-sm font-bold transition-all ${
                      page === pageNum
                        ? 'bg-primary text-white shadow-lg shadow-primary/30'
                        : 'bg-neutral-900 border border-border text-neutral-400 hover:border-primary hover:text-primary'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => { setPage(p => Math.min(Math.ceil(totalCount / PAGE_SIZE), p + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={page === Math.ceil(totalCount / PAGE_SIZE)}
              className="px-5 py-2 rounded-xl bg-neutral-900 border border-border text-sm font-bold disabled:opacity-30 disabled:cursor-not-allowed hover:border-primary hover:text-primary transition-all"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      <AdModal
        ad={selectedAd}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
