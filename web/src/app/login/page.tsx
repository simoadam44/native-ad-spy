"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Globe, Mail, Lock, Loader2, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, isRegister: !isLogin }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Authentication failed');
      }

      if (data.needsConfirmation) {
        alert("Please check your email to confirm your account!");
      } else {
        window.location.href = '/dashboard';
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(124,58,237,0.15),transparent_50%)]" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-neutral-900 border border-neutral-800 rounded-3xl p-8 relative z-10"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 mb-4 text-purple-500">
            <Globe size={32} />
          </div>
          <h1 className="text-3xl font-bold uppercase tracking-wider">Native Spy</h1>
          <p className="text-neutral-500 text-sm mt-2">Premium Ad Intelligence Platform</p>
        </div>

        <div className="flex bg-neutral-800 rounded-xl p-1 mb-8">
          <button 
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${isLogin ? 'bg-purple-500 text-white' : 'text-neutral-500 hover:text-white'}`}
          >
            LOGIN
          </button>
          <button 
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${!isLogin ? 'bg-purple-500 text-white' : 'text-neutral-500 hover:text-white'}`}
          >
            REGISTER
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs uppercase font-bold text-neutral-500 px-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3.5 text-neutral-600" size={18} />
              <input 
                type="email" 
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-xl py-3 pl-10 pr-4 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs uppercase font-bold text-neutral-500 px-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3.5 text-neutral-600" size={18} />
              <input 
                type="password" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-xl py-3 pl-10 pr-4 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                required
              />
            </div>
          </div>

          {error && (
            <div className="text-red-500 text-xs bg-red-500/10 p-3 rounded-lg border border-red-500/20">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-4 rounded-xl mt-6 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : (isLogin ? "SIGN IN" : "CREATE ACCOUNT")}
            {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        <p className="text-center text-neutral-600 text-xs mt-8">
          By continuing, you agree to our Terms of Service and Privacy Policy.
        </p>
      </motion.div>
    </div>
  );
}