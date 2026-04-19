"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { 
  Users, 
  Settings, 
  Activity, 
  Play, 
  CheckCircle2,
  Trash2,
  UserPlus,
  RefreshCw,
  BarChart3,
  CreditCard,
  ShieldAlert,
  Search,
  MoreVertical,
  Terminal,
  Database,
  ShieldCheck,
  Zap,
  Target,
  Globe
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [users, setUsers] = useState<any[]>([]);
  const [ads, setAds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const { data: u } = await supabase.from("users").select("*").order("created_at", { ascending: false });
      const { data: a } = await supabase.from("ads").select("*").limit(20).order("created_at", { ascending: false });
      setUsers(u || []);
      setAds(a || []);
      setLoading(false);
    }
    loadData();
  }, []);

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "users", label: "Users", icon: Users },
    { id: "review", label: "Review Queue", icon: ShieldCheck },
    { id: "lab", label: "Teaching Lab", icon: Zap },
    { id: "subs", label: "Subscriptions", icon: CreditCard },
    { id: "ads", label: "Ads Health", icon: Database },
    { id: "crawler", label: "Crawler Hub", icon: Terminal },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-20 p-8">
      <div className="flex justify-between items-center bg-card border border-border p-8 rounded-3xl relative overflow-hidden">
        <div className="relative z-10">
          <h1 className="text-5xl font-bold font-syne uppercase tracking-tighter">Command Center</h1>
          <p className="text-neutral-500 mt-2 font-medium">Native Spy Platform Administration</p>
        </div>
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-primary/10 to-transparent" />
        <div className="relative z-10">
           <button className="bg-primary hover:bg-primary/90 text-white font-bold py-3 px-6 rounded-xl flex items-center gap-2 shadow-xl shadow-primary/20 transition-all">
             <RefreshCw size={18} /> Refresh System
           </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-neutral-900 p-1 rounded-2xl overflow-x-auto border border-border">
        {tabs.map((tab) => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-card text-white shadow-lg border border-white/5' : 'text-neutral-500 hover:text-white'}`}
          >
            <tab.icon size={16} /> {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div 
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="space-y-8"
        >
          {activeTab === "overview" && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {[
                  { label: "Total Users", value: users.length, icon: Users, color: "text-blue-500" },
                  { label: "Active Subs", value: users.filter(u => u.plan !== 'free').length, icon: CreditCard, color: "text-green-500" },
                  { label: "Total Ads", value: "45,210", icon: Database, color: "text-primary" },
                  { label: "New Today", value: "+840", icon: Activity, color: "text-accent" },
                ].map((stat) => (
                  <div key={stat.label} className="bg-card border border-border p-6 rounded-2xl group hover:border-primary/20 transition-all">
                    <stat.icon size={24} className={`${stat.color} mb-4 group-hover:scale-110 transition-transform`} />
                    <div className="text-neutral-500 text-[10px] font-black uppercase tracking-widest">{stat.label}</div>
                    <div className="text-3xl font-bold font-syne mt-1">{stat.value}</div>
                  </div>
                ))}
              </div>
              
              <div className="grid grid-cols-2 gap-8">
                 <div className="bg-card border border-border rounded-3xl p-6 h-80 flex flex-col items-center justify-center text-neutral-600">
                    <BarChart3 size={48} className="mb-4 opacity-20" />
                    <p className="text-sm font-bold uppercase tracking-widest">Network Distribution Chart</p>
                 </div>
                 <div className="bg-card border border-border rounded-3xl p-6 h-80 flex flex-col items-center justify-center text-neutral-600">
                    <Activity size={48} className="mb-4 opacity-20" />
                    <p className="text-sm font-bold uppercase tracking-widest">Growth Trends</p>
                 </div>
              </div>
            </>
          )}

          {activeTab === "users" && (
            <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-2xl">
              <div className="p-6 border-b border-border bg-white/5 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Users size={18} className="text-primary" />
                  <h2 className="font-bold font-syne uppercase">User Registry</h2>
                </div>
                <div className="flex gap-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 text-neutral-600" size={14} />
                    <input type="text" placeholder="Search users..." className="bg-neutral-900 border border-border rounded-lg py-1.5 pl-8 pr-4 text-xs focus:border-primary outline-none" />
                  </div>
                  <button className="bg-white/5 border border-border hover:bg-white/10 p-2 rounded-lg text-neutral-400">
                    <UserPlus size={16} />
                  </button>
                </div>
              </div>
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] font-black text-neutral-500 uppercase tracking-widest bg-neutral-900/50">
                    <th className="px-6 py-4">Identity</th>
                    <th className="px-6 py-4">Plan Status</th>
                    <th className="px-6 py-4">Joined</th>
                    <th className="px-6 py-4">Activity</th>
                    <th className="px-6 py-4 text-right">Control</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-sm">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-white/5 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center font-bold text-primary group-hover:bg-primary group-hover:text-white transition-all">
                            {user.email[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="font-bold">{user.email}</p>
                            <p className="text-[10px] text-neutral-600 font-mono tracking-tighter">ID: {user.id.slice(0, 8)}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <select 
                          className="bg-neutral-900 border border-border rounded-lg px-3 py-1 text-xs font-bold text-primary appearance-none cursor-pointer hover:border-primary transition-all"
                          defaultValue={user.plan || 'free'}
                        >
                          <option value="free">FREE</option>
                          <option value="pro">PRO</option>
                          <option value="agency">AGENCY</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 text-neutral-400 font-medium">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                           <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                           <span className="text-[10px] font-bold text-neutral-500">ONLINE</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2 translate-x-4 opacity-0 group-hover:translate-x-0 group-hover:opacity-100 transition-all">
                          <button className="p-2 hover:bg-neutral-800 rounded-lg text-neutral-500 hover:text-white" title="Reset AI Usage">
                             <RefreshCw size={14} />
                          </button>
                          <button className="p-2 hover:bg-red-500/20 rounded-lg text-neutral-500 hover:text-red-500" title="Delete User">
                             <Trash2 size={14} />
                          </button>
                          <button className="p-2 hover:bg-neutral-800 rounded-lg text-neutral-500">
                             <MoreVertical size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "crawler" && (
             <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
               <div className="bg-card border border-border rounded-3xl p-8 space-y-6">
                 <div className="flex items-center gap-2 mb-4">
                   <Terminal size={24} className="text-secondary" />
                   <h2 className="text-xl font-bold font-syne uppercase">Crawler Status</h2>
                 </div>
                 {[
                   { name: "Taboola Master", status: "Running", color: "bg-green-500" },
                   { name: "MGID Scraper", status: "Sleeping", color: "bg-blue-500" },
                   { name: "Outbrain Bot", status: "Error", color: "bg-red-500" },
                   { name: "Revcontent API", status: "Idle", color: "bg-neutral-700" },
                 ].map((c) => (
                   <div key={c.name} className="flex justify-between items-center p-4 bg-neutral-900 border border-border rounded-2xl">
                     <span className="font-bold text-sm">{c.name}</span>
                     <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold text-neutral-500 uppercase">{c.status}</span>
                        <div className={`w-3 h-3 rounded-full ${c.color}`} />
                     </div>
                   </div>
                 ))}
                 <button className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-4 rounded-2xl flex items-center justify-center gap-2 mt-8 shadow-lg shadow-primary/20 transition-all">
                   <Play size={18} fill="currentColor" /> Trigger Global Rescan
                 </button>
               </div>

               <div className="bg-neutral-950 border border-border rounded-3xl p-8 font-mono text-[10px] space-y-2 overflow-y-auto max-h-[500px]">
                  <p className="text-neutral-500">[2024-03-26 23:30:12] INFO: Connecting to MGID API...</p>
                  <p className="text-neutral-500">[2024-03-26 23:30:15] SUCCESS: Found 124 new creatives.</p>
                  <p className="text-red-500">[2024-03-26 23:30:18] ERROR: Outbrain proxy timeout.</p>
                  <p className="text-neutral-500">[2024-03-26 23:30:22] INFO: Uploading 124 images to Supabase Storage...</p>
                  <p className="text-green-500">[2024-03-26 23:30:45] SYNC: Database updated successfully.</p>
                  <div className="animate-pulse flex items-center gap-2 pt-4">
                    <span className="text-primary font-bold">{`>`}</span>
                    <span className="text-white">Awaiting next instruction...</span>
                  </div>
               </div>
             </div>
          )}

          {activeTab === "review" && (
            <div className="bg-card border border-border rounded-3xl overflow-hidden shadow-2xl">
              <div className="p-6 border-b border-border bg-white/5 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-emerald-400" />
                  <h2 className="font-bold font-syne uppercase">Manual Review Queue</h2>
                </div>
                <div className="text-[10px] font-black text-neutral-500 bg-neutral-900 px-3 py-1 rounded-full uppercase tracking-widest border border-border">
                  Confidence Threshold: <span className="text-emerald-400">Low</span>
                </div>
              </div>
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] font-black text-neutral-500 uppercase tracking-widest bg-neutral-900/50">
                    <th className="px-6 py-4">Ad Portfolio</th>
                    <th className="px-6 py-4">Forensic Detection</th>
                    <th className="px-6 py-4">Detected Params</th>
                    <th className="px-6 py-4 text-right">Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-sm">
                   {ads.filter(a => a.needs_review || (a.ad_type === 'Affiliate' && !a.affiliate_network)).map((ad) => (
                    <tr key={ad.id} className="hover:bg-white/5 transition-colors group">
                      <td className="px-6 py-4 max-w-[300px]">
                        <div className="flex items-center gap-3">
                           <div className="w-12 h-12 rounded-lg bg-neutral-800 overflow-hidden shrink-0 border border-white/5">
                              <img src={ad.image_url} className="w-full h-full object-cover" />
                           </div>
                           <div className="min-w-0">
                              <p className="font-bold text-xs truncate mb-1">{ad.title}</p>
                              <div className="flex items-center gap-1.5">
                                 <span className="text-[8px] font-black uppercase px-1.5 py-0.5 bg-blue-600/20 text-blue-400 rounded border border-blue-500/20">{ad.network}</span>
                                 <span className="text-[8px] font-black uppercase px-1.5 py-0.5 bg-neutral-800 text-neutral-400 rounded">{ad.country_code || 'US'}</span>
                              </div>
                           </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                         <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                               <Globe size={10} className="text-neutral-500" />
                               <span className="text-[10px] font-bold text-neutral-300 truncate max-w-[150px]">{ad.offer_domain || 'Unknown Domain'}</span>
                            </div>
                            <div className="flex items-center gap-2">
                               <Zap size={10} className="text-amber-400" />
                               <span className="text-[10px] font-bold text-neutral-400">{ad.tracker_tool || 'No Tracker'}</span>
                            </div>
                         </div>
                      </td>
                      <td className="px-6 py-4">
                         <div className="flex flex-wrap gap-1">
                            {ad.affiliate_id && <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 rounded text-[9px] font-black">AFF: {ad.affiliate_id}</span>}
                            {ad.offer_id && <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-500 rounded text-[9px] font-black">OFF: {ad.offer_id}</span>}
                            {!ad.affiliate_id && !ad.offer_id && <span className="text-[10px] italic text-neutral-600">None detected</span>}
                         </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                         <div className="flex justify-end gap-2">
                            <button 
                              className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-[10px] font-black uppercase rounded-lg transition-all shadow-lg shadow-emerald-500/20"
                              onClick={async () => {
                                  await supabase.table("ads").update({ needs_review: false, network_confidence: 'high' }).eq("id", ad.id);
                                  // Refresh logic
                              }}
                            >
                               Approve
                            </button>
                            <button className="p-2 hover:bg-neutral-800 rounded-lg text-neutral-500">
                               <Settings size={14} />
                            </button>
                         </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {ads.filter(a => a.needs_review || (a.ad_type === 'Affiliate' && !a.affiliate_network)).length === 0 && (
                <div className="p-20 text-center text-neutral-600">
                   <CheckCircle2 size={48} className="mx-auto mb-4 opacity-10" />
                   <p className="text-sm font-bold uppercase tracking-widest">Queue is clear</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "lab" && (
             <div className="space-y-8">
               <div className="bg-card border border-border p-8 rounded-3xl relative overflow-hidden">
                 <div className="flex items-center gap-3 mb-6 relative z-10">
                    <Zap className="text-amber-400" size={24} />
                    <div>
                      <h2 className="text-xl font-bold font-syne uppercase text-white/90">Forensic Knowledge Base</h2>
                      <p className="text-neutral-500 text-xs font-medium">Correction results here "teach" the tool to recognize domains correctly in the future.</p>
                    </div>
                 </div>
                 <div className="absolute top-0 right-0 w-64 h-64 bg-amber-400/5 blur-[100px] -mr-32 -mt-32" />

                 <div className="bg-neutral-900/50 border border-border rounded-2xl overflow-hidden shadow-inner">
                   <table className="w-full text-left">
                     <thead>
                       <tr className="text-[10px] font-black text-neutral-500 uppercase tracking-widest border-b border-border bg-neutral-900">
                         <th className="px-6 py-4">Creative / Domain</th>
                         <th className="px-6 py-4">AI Prediction</th>
                         <th className="px-6 py-4 text-right pr-6">Human Correction</th>
                       </tr>
                     </thead>
                     <tbody className="divide-y divide-border text-sm">
                        {ads.slice(0, 15).map((ad) => (
                         <tr key={ad.id} className="hover:bg-white/5 transition-colors group">
                           <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg overflow-hidden shrink-0 border border-white/5 shadow-sm">
                                   <img src={ad.image_url} className="w-full h-full object-cover" />
                                </div>
                                <div className="min-w-0">
                                   <p className="font-bold text-xs truncate max-w-[200px] text-neutral-200">{ad.title}</p>
                                   <p className="text-[10px] text-neutral-600 font-mono italic truncate">{ad.offer_domain || 'Unknown Domain'}</p>
                                </div>
                              </div>
                           </td>
                           <td className="px-6 py-4">
                              <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded border ${ad.ad_type === 'Affiliate' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-blue-500/10 text-blue-500 border-blue-500/20'}`}>
                                {ad.ad_type}
                              </span>
                           </td>
                           <td className="px-6 py-4 text-right pr-6">
                              <div className="flex justify-end gap-2">
                                <button 
                                  className="px-4 py-1.5 bg-emerald-500/10 border border-emerald-500/50 text-emerald-500 text-[10px] font-black uppercase rounded-lg hover:bg-emerald-500 hover:text-white transition-all transform active:scale-95 shadow-sm"
                                  onClick={async () => {
                                      const domain = ad.offer_domain || (ad.landing ? new URL(ad.landing).hostname : null);
                                      if (!domain) {
                                          alert("No domain detected for this ad.");
                                          return;
                                      }
                                      await supabase.from("forensic_feedback").upsert({ domain, forced_type: 'Affiliate', notes: 'Manual correction' });
                                      await supabase.from("ads").update({ ad_type: 'Affiliate', classification_confidence: 'high', classification_reason: 'knowledge_base_override (manual_correction)', needs_review: false }).eq("id", ad.id);
                                      alert(`Learned: ${domain} is Affiliate`);
                                  }}
                                >
                                  Affiliate
                                </button>
                                <button 
                                  className="px-4 py-1.5 bg-blue-500/10 border border-blue-500/50 text-blue-500 text-[10px] font-black uppercase rounded-lg hover:bg-blue-500 hover:text-white transition-all transform active:scale-95 shadow-sm"
                                  onClick={async () => {
                                      const domain = ad.offer_domain || (ad.landing ? new URL(ad.landing).hostname : null);
                                      if (!domain) {
                                          alert("No domain detected for this ad.");
                                          return;
                                      }
                                      await supabase.from("forensic_feedback").upsert({ domain, forced_type: 'Arbitrage', notes: 'Manual correction' });
                                      await supabase.from("ads").update({ ad_type: 'Arbitrage', classification_confidence: 'high', classification_reason: 'knowledge_base_override (manual_correction)', needs_review: false }).eq("id", ad.id);
                                      alert(`Learned: ${domain} is Arbitrage`);
                                  }}
                                >
                                  Arbitrage
                                </button>
                              </div>
                           </td>
                         </tr>
                        ))}
                     </tbody>
                   </table>
                 </div>
                 {ads.length === 0 && <div className="py-20 text-center text-neutral-600 font-bold uppercase tracking-widest text-xs">No ads analyzed recently</div>}
               </div>
             </div>
          )}

          {activeTab === "settings" && (
            <div className="max-w-2xl bg-card border border-border rounded-3xl p-8 space-y-8">
               <div className="space-y-4">
                 <label className="text-xs font-black uppercase tracking-widest text-neutral-500">Site Configuration</label>
                 <div className="space-y-2">
                    <p className="text-xs font-bold px-1 text-neutral-400">Platform Name</p>
                    <input type="text" defaultValue="Native Spy" className="w-full bg-neutral-900 border border-border rounded-xl px-4 py-3 outline-none focus:border-primary transition-all text-sm font-bold text-white shadow-inner" />
                 </div>
                 <div className="flex items-center justify-between p-4 bg-neutral-900 border border-border rounded-2xl">
                    <div>
                       <p className="text-sm font-bold text-neutral-200">Maintenance Mode</p>
                       <p className="text-[10px] text-neutral-500">Locks the platform for user access during updates.</p>
                    </div>
                    <div className="w-12 h-6 bg-neutral-800 rounded-full cursor-pointer p-1 relative border border-border shadow-inner">
                       <div className="w-4 h-4 bg-neutral-600 rounded-full" />
                    </div>
                 </div>
               </div>
               <div className="pt-8 border-t border-border flex justify-end">
                  <button className="bg-primary hover:bg-primary/90 text-white font-black py-4 px-12 rounded-2xl transition-all shadow-xl shadow-primary/30 uppercase tracking-[0.2em] text-[10px]">
                    Save Changes
                  </button>
               </div>
            </div>
          )}

          {/* Fallback for other tabs */}
          {["subs", "ads"].includes(activeTab) && (
            <div className="bg-card border border-border rounded-3xl p-20 text-center flex flex-col items-center justify-center opacity-50">
               <ShieldAlert size={64} className="mb-4 text-neutral-800" />
               <p className="font-bold uppercase tracking-widest text-neutral-500">{activeTab.toUpperCase()} Module in Development</p>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
