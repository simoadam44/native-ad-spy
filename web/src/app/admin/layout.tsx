import { Globe, ShieldAlert } from "lucide-react";
import Link from "next/link";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Admin Top Bar */}
      <header className="bg-red-950/30 border-b border-red-900/40 px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-red-500/20 rounded-lg text-red-400">
            <ShieldAlert size={18} />
          </div>
          <span className="text-red-400 text-xs font-black uppercase tracking-widest">
            Admin Zone — Restricted Access
          </span>
        </div>
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-xs text-neutral-500 hover:text-white transition-all font-bold"
        >
          <Globe size={14} /> Back to Dashboard
        </Link>
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}
