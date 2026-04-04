import { ArrowRight, BarChart3, Globe, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 text-center">
      <div className="max-w-4xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-1000">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-primary/10 rounded-2xl border border-primary/20">
            <Globe className="w-12 h-12 text-primary" />
          </div>
        </div>
        
        <h1 className="text-6xl font-bold tracking-tight font-syne">
          Explore the world of <span className="text-primary italic">Native Ads</span> with precision.
        </h1>
        
        <p className="text-xl text-neutral-400 max-w-2xl mx-auto font-sans leading-relaxed">
          The most powerful, AI-driven spy tool for Taboola, MGID, Outbrain, and Revcontent. 
          Uncover winning angles, high-performing headlines, and trending creatives in seconds.
        </p>
        
        <div className="flex gap-4 justify-center pt-8">
          <button className="px-8 py-4 bg-primary rounded-full font-bold text-lg hover:scale-105 transition-all flex items-center gap-2">
            Get Started Now <ArrowRight className="w-5 h-5" />
          </button>
          <button className="px-8 py-4 bg-white/5 border border-white/10 rounded-full font-bold text-lg hover:bg-white/10 transition-all">
            View Live Demo
          </button>
        </div>

        <div className="grid grid-cols-3 gap-8 pt-20 border-t border-white/5">
          <div className="space-y-2">
            <BarChart3 className="w-6 h-6 text-secondary mx-auto" />
            <h3 className="font-bold">Real-time Stats</h3>
            <p className="text-sm text-neutral-500">Global tracking across 4 major networks.</p>
          </div>
          <div className="space-y-2">
            <ShieldCheck className="w-6 h-6 text-accent mx-auto" />
            <h3 className="font-bold">AI Verification</h3>
            <p className="text-sm text-neutral-500">Claude 3.5 Sonnet analysis for every ad.</p>
          </div>
          <div className="space-y-2">
            <Globe className="w-6 h-6 text-primary mx-auto" />
            <h3 className="font-bold">Global Reach</h3>
            <p className="text-sm text-neutral-500">Search millions of ads in 50+ countries.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
