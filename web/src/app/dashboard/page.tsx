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

const COUNTRY_NAMES: Record<string, string> = {
  US: "United States", GB: "United Kingdom", CA: "Canada", AU: "Australia", 
  DE: "Germany", FR: "France", IT: "Italy", ES: "Spain", NL: "Netherlands", 
  SE: "Sweden", SA: "Saudi Arabia", AE: "United Arab Emirates", 
  MA: "Morocco", EG: "Egypt", ZA: "South Africa", JP: "Japan", 
  KR: "South Korea", IN: "India", BR: "Brazil", MX: "Mexico"
};

const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "fr", name: "French" },
  { code: "ar", name: "Arabic" },
  { code: "es", name: "Spanish" },
  { code: "pt", name: "Portuguese" },
  { code: "de", name: "German" },
  { code: "it", name: "Italian" },
  { code: "tr", name: "Turkish" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "zh", name: "Chinese" },
  { code: "ru", name: "Russian" },
  { code: "hi", name: "Hindi" }
];

const PAGE_SIZE = 30;

// Cross-platform Flag Component using FlagCDN (Windows doesn't support Emoji flags natively)
const Flag = ({ code, className = "" }: { code: string, className?: string }) => {
  if (!code || code === "all") return null;
  return (
    <img 
      src={`https://flagcdn.com/w20/${code.toLowerCase()}.png`} 
      alt={code} 
      className={`inline-block rounded-[2px] object-cover ${className}`}
      style={{ width: '16px', height: '12px' }}
    />
  );
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
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("newest");
  const [minImpressions, setMinImpressions] = useState(0);

  const loadAds = useCallback(async () => {
    setLoading(true);
    const offset = (page - 1) * PAGE_SIZE;
    let query = supabase.from("ads").select("*", { count: "exact" });

    if (search) query = query.ilike("title", `%${search}%`);
    if (selectedNetworks.length > 0) {
      // Map UI labels to database values (especially for OUTBRAIN/MGID casing)
      const dbNetworks = selectedNetworks.map(n => {
        if (n === "Outbrain") return "OUTBRAIN";
        return n;
      });
      query = query.in("network", dbNetworks);
    }
    if (selectedCountries.length > 0) query = query.in("country_code", selectedCountries);
    if (selectedLanguages.length > 0) query = query.in("language", selectedLanguages);
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
  }, [search, selectedNetworks, selectedCountries, selectedLanguages, sortBy, minImpressions, page, toggleNetwork]);

  useEffect(() => { loadAds(); }, [loadAds]);

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1); }, [search, selectedNetworks, selectedCountries, selectedLanguages, sortBy, minImpressions]);

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

  const toggleLanguage = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === "all") setSelectedLanguages([]);
    else if (!selectedLanguages.includes(value)) setSelectedLanguages([...selectedLanguages, value]);
  };

  const removeLanguage = (code: string) => {
    setSelectedLanguages(prev => prev.filter(c => c !== code));
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

        <div className="flex items-center gap-2">
          <select
            onChange={toggleCountry}
            className="bg-neutral-900 border border-border rounded-xl px-3 py-2 text-sm focus:border-primary outline-none"
            value=""
          >
            <option value="" disabled>+ Country</option>
            <option value="all">All Countries</option>
            {COUNTRIES.map(c => (
              <option key={c} value={c}>{COUNTRY_NAMES[c] || c}</option>
            ))}
          </select>

          <select
            onChange={toggleLanguage}
            className="bg-neutral-900 border border-border rounded-xl px-3 py-2 text-sm focus:border-primary outline-none"
            value=""
          >
            <option value="" disabled>+ Language</option>
            <option value="all">All Languages</option>
            {LANGUAGES.map(lang => (
              <option key={lang.code} value={lang.code}>{lang.name}</option>
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

        { (selectedNetworks.length > 0 || selectedCountries.length > 0 || selectedLanguages.length > 0) && (
          <button
            onClick={() => { setSelectedNetworks([]); setSelectedCountries([]); setSelectedLanguages([]); }}
            className="flex items-center gap-1 text-xs text-neutral-500 hover:text-white transition-all ml-auto"
          >
            <X size={14} /> Clear Filters
          </button>
        )}
      </div>

      {/* Filter Tags */}
      {(selectedCountries.length > 0 || selectedLanguages.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {selectedCountries.map(code => (
            <span key={code} className="flex items-center gap-1.5 bg-neutral-800 text-white px-2 py-1 rounded text-[10px] font-bold border border-white/5">
              <Flag code={code} /> {COUNTRY_NAMES[code] || code}
              <button onClick={() => removeCountry(code)} className="hover:text-red-400 ml-1"><X size={10}/></button>
            </span>
          ))}
          {selectedLanguages.map(code => (
            <span key={code} className="flex items-center gap-1.5 bg-neutral-800 text-white px-2 py-1 rounded text-[10px] font-bold border border-white/5">
              <BrainCircuit size={10} className="text-secondary" /> {LANGUAGES.find(l => l.code === code)?.name || code}
              <button onClick={() => removeLanguage(code)} className="hover:text-red-400 ml-1"><X size={10}/></button>
            </span>
          ))}
        </div>
      )}

      {/* Ad Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="h-44 bg-white/5 animate-pulse relative">
                <div className="absolute top-2.5 left-2.5 flex flex-col gap-1">
                   <div className="w-12 h-4 bg-white/10 rounded-md" />
                   <div className="w-16 h-4 bg-white/10 rounded-md" />
                </div>
              </div>
              <div className="p-4 space-y-4">
                <div className="space-y-2">
                  <div className="h-3 bg-white/10 rounded w-full animate-pulse" />
                  <div className="h-3 bg-white/10 rounded w-2/3 animate-pulse" />
                </div>
                <div className="pt-3 border-t border-white/5 flex justify-between items-center">
                  <div className="w-12 h-2 bg-white/5 rounded" />
                  <div className="w-16 h-2 bg-white/5 rounded" />
                </div>
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
                className="bg-[#1A1A23] border border-white/5 rounded-2xl overflow-hidden group hover:border-primary/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.1)] transition-all duration-500 cursor-pointer flex flex-col relative"
              >
                {/* Premium Shine Effect on Hover */}
                <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                
                <div className="relative h-44 overflow-hidden">
                  <img
                    src={ad.image || `https://picsum.photos/seed/${ad.id}/400/250`}
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                    alt={ad.title}
                    onError={e => { (e.target as HTMLImageElement).src = `https://picsum.photos/seed/${i}/400/250`; }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#13131A] via-transparent to-transparent opacity-60 group-hover:opacity-40 transition-opacity" />
                  
                  <div className="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
                    <span className={`px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider backdrop-blur-md shadow-lg ${
                      ad.network === 'Taboola' ? 'bg-blue-600/80' : 
                      ad.network === 'MGID' ? 'bg-purple-600/80' : 
                      ad.network === 'Outbrain' ? 'bg-orange-600/80' : 'bg-green-600/80'
                    } text-white`}>
                      {ad.network}
                    </span>
                    {ad.country_code && (
                      <span className="px-2.5 py-1 flex items-center gap-1.5 rounded-lg text-[9px] font-black uppercase tracking-wider bg-black/40 backdrop-blur-md text-white border border-white/5 shadow-lg">
                        <Flag code={ad.country_code} /> {ad.country_code}
                      </span>
                    )}
                  </div>

                  <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all duration-300 flex gap-2 z-10">
                    <button
                      onClick={e => toggleFav(e, ad.id)}
                      className={`p-2 rounded-xl backdrop-blur-xl transition-all shadow-xl ${favs.includes(ad.id) ? 'bg-red-500 text-white' : 'bg-white/10 text-white hover:bg-white/20'}`}
                    >
                      <Heart size={15} fill={favs.includes(ad.id) ? "currentColor" : "none"} />
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); setSelectedAd(ad); setIsModalOpen(true); }}
                      className="p-2 rounded-xl backdrop-blur-xl bg-primary/20 text-primary border border-primary/20 hover:bg-primary hover:text-white transition-all shadow-xl"
                    >
                      <BrainCircuit size={15} />
                    </button>
                  </div>
                </div>

                <div className="p-5 flex flex-col flex-1 relative z-10">
                  <h3 className="text-[13px] font-bold font-syne line-clamp-2 leading-snug group-hover:text-primary transition-colors duration-300 mb-4">
                    {ad.title}
                  </h3>
                  <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/[0.03]">
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                        <Flame size={10} className="text-primary" />
                      </div>
                      <span className="text-[10px] font-black text-neutral-400 tracking-tight">
                        {(ad.impressions || 0).toLocaleString()}
                      </span>
                    </div>
                    <span className="text-[9px] font-bold text-neutral-600 uppercase tracking-tighter">
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
