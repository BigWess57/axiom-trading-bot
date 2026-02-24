"use client";

import { usePulseSocket } from "@/hooks/usePulseSocket";
import { TokenCard } from "./TokenCard";
import { Activity } from "lucide-react";

const CategoryColumn = ({ title, tokens, color, solPrice }: { title: string; tokens: any[]; color: string; solPrice: number | null }) => (
  <div className="flex-1 min-w-[400px] border-x border-slate-800">
    <div className={`sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm border-b border-${color}-900/30 p-4 mb-4`}>
      <h2 className={`text-lg font-bold text-${color}-400 flex items-center gap-2`}>
        <Activity className="w-5 h-5" />
        {title}
        <span className="text-sm text-slate-500">({tokens.length})</span>
      </h2>
    </div>
    
    <div className="space-y-3 px-4 pb-4">
      {tokens.length === 0 ? (
        <div className="text-center text-slate-600 py-12">
          No tokens in this category
        </div>
      ) : (
        tokens.map((token) => (
          <TokenCard solPrice={solPrice} key={token.pair_address} token={token} />
        ))
      )}
    </div>
  </div>
);

export const PulseFeed: React.FC = () => {
  const { tokensByCategory, isConnected, lastUpdate, solPrice } = usePulseSocket();
  
  return (
    <div className="min-h-screen bg-linear-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-linear-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Pulse Tracker
            </h1>
            <p className="text-sm text-slate-400">Real-time Solana token monitoring</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
              <span className="text-sm text-slate-400">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <div className="text-xs text-slate-500" suppressHydrationWarning>
              {lastUpdate.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* 3-Column Layout */}
      <div className="flex p-6 overflow-x-auto">
        <CategoryColumn 
          title="🆕 New Pairs" 
          tokens={tokensByCategory.newPairs}
          color="blue"
          solPrice={solPrice}
        />
        <CategoryColumn 
          title="🎯 Final Stretch" 
          tokens={tokensByCategory.finalStretch}
          color="purple"
          solPrice={solPrice}
        />
        <CategoryColumn 
          title="🚀 Migrated" 
          tokens={tokensByCategory.migrated}
          color="green"
          solPrice={solPrice}
        />
      </div>
    </div>
  );
};
