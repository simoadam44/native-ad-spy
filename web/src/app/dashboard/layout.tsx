"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  BarChart3, 
  Globe, 
  Search, 
  Heart, 
  ShieldCheck, 
  Settings, 
  LogOut,
  LayoutDashboard,
  Menu,
  X,
  CreditCard
} from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const pathname = usePathname();

  const menuItems = [
    { icon: LayoutDashboard, label: "Ads Discovery", href: "/dashboard" },
    { icon: Heart, label: "My Favorites", href: "/dashboard/favorites" },
    { icon: BarChart3, label: "Niche Reports", href: "/dashboard/reports" },
    { icon: ShieldCheck, label: "Admin Panel", href: "/admin" },
  ];

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <aside className={`bg-card border-r border-border transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-20'} flex flex-col`}>
        <div className="p-6 flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg text-primary">
            <Globe size={24} />
          </div>
          {sidebarOpen && <span className="font-bold font-syne text-xl tracking-tight uppercase">Native Spy</span>}
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          {menuItems.map((item) => (
            <Link 
              key={item.href}
              href={item.href}
              className={`flex items-center gap-4 py-3 px-3 rounded-xl transition-all group ${pathname === item.href ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-neutral-500 hover:bg-white/5 hover:text-white'}`}
            >
              <item.icon size={20} className={pathname === item.href ? 'text-white' : 'group-hover:text-primary transition-colors'} />
              {sidebarOpen && <span className="font-bold text-sm tracking-wide">{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="p-4 mt-auto">
          <div className={`bg-neutral-900 border border-border rounded-2xl p-4 ${!sidebarOpen && 'hidden'}`}>
            <div className="flex items-center gap-2 mb-2">
              <CreditCard size={14} className="text-secondary" />
              <span className="text-[10px] uppercase font-bold text-neutral-500">PRO PLAN</span>
            </div>
            <div className="h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
              <div className="h-full bg-secondary w-1/2 rounded-full" />
            </div>
            <p className="text-[10px] text-neutral-500 mt-2">24 / 50 AI Credits Used</p>
          </div>

          <button className="flex items-center gap-4 py-3 px-3 rounded-xl transition-all text-neutral-500 hover:bg-red-500/10 hover:text-red-500 w-full mt-4">
            <LogOut size={20} />
            {sidebarOpen && <span className="font-bold text-sm tracking-wide">Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 border-b border-border bg-background/50 backdrop-blur-md flex items-center justify-between px-8 z-10">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-white/5 rounded-lg text-neutral-400">
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          <div className="flex-1 max-w-xl mx-8 relative">
            <Search className="absolute left-3 top-2.5 text-neutral-600" size={18} />
            <input 
              type="text" 
              placeholder="Search millions of ads..." 
              className="w-full bg-neutral-900 border border-border rounded-xl py-2 pl-10 pr-4 text-sm focus:border-primary outline-none"
            />
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-bold">Admin User</p>
              <p className="text-[10px] text-neutral-500 uppercase tracking-tighter">simoadam@admin.com</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center font-bold text-primary">
              A
            </div>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto p-8 custom-scrollbar">
          {children}
        </section>
      </main>
    </div>
  );
}
