"use client";

import React from "react";
import { motion } from "framer-motion";
import { Copy, MessageSquare, MonitorPlay, Trophy, Zap, ExternalLink, Twitter, Globe, Send, Users, Eye, Crown } from "lucide-react";
import { PulseToken } from "@/utils/types";
import { cn } from "@/utils/utils";
import { TokenSOL } from '@web3icons/react'
import { DebugFieldsPanel } from "./DebugFieldsPanel";

interface TokenCardProps {
    token: PulseToken;
    solPrice: number | null;
}

const formatValueInUSD = (val: number, solPrice: number | null) => {
    if (!solPrice) {
        return "--"
    }

    if (val * solPrice >= 1000 && val * solPrice < 100000) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 1,
        }).format(val * solPrice / 1000) + "K";
    }
    if (val * solPrice >= 100000) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 0,
        }).format(val * solPrice / 1000) + "K";
    }
    
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
    }).format(val * solPrice);
};

// Helper for SOL Custom Formatting
const formatValueInSOL = (val: number) => {
    if (val === 0) return "0";
    
    // Big enough: 2 decimals
    if (val >= 1) {
        return new Intl.NumberFormat('en-US', { 
            maximumFractionDigits: 2,
            minimumFractionDigits: 0
        }).format(val);
    }
    
    const str = val.toFixed(20);
    // Standard small: < 1 but not tiny (e.g. 0.5, 0.01)
    // Check leading zeros after decimal
    const match = str.match(/^0\.(0+)(\d+)/);
    
    if (match) {
        const zeros = match[1].length;
        const significant = match[2];
        
        // "Very small": If 2 or more zeros (e.g. 0.005 -> 0.0₂5)
        if (zeros >= 2) {
             return (
                 <span className="inline-flex items-baseline">
                     0.0
                     <sub className="text-[10px] font-bold mx-px">{zeros}</sub>
                     {significant.slice(0, 3)}
                 </span>
             );
        }
    }
    
    // Otherwise 3 decimals for < 1
    return val.toFixed(3);
};

const timeAgo = (dateStr: string | null) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h`;
};

// Helper Component for Badges
const MetricBadge = ({ label, value, color = "slate", icon: Icon }: { label: string; value: string | number; color?: string; icon?: React.ElementType }) => (
    <div className={`flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-${color}-900/30 border border-${color}-700/50 text-${color}-400`}>
        {Icon && <Icon className="w-3 h-3" />}
        <span className="font-bold">{label}</span>
        <span className="font-mono">{value}</span>
    </div>
);



export const TokenCard = React.memo(({ token, solPrice }: TokenCardProps) => {
  return (
    <div className="group relative bg-slate-900/40 border border-slate-800 hover:border-slate-600 rounded-lg p-3 transition-all hover:bg-slate-900/60 font-sans flex flex-col gap-2">
        {/* UPPER SECTION: Identity & Stats */}
        <div className="flex justify-between items-start gap-3">
            {/* LEFT: Identity & Metadata */}
            <div className="flex gap-3 flex-1 min-w-0">
                {/* Image */}
                <div className="relative w-12 h-12 shrink-0 rounded-md bg-slate-800 overflow-hidden border border-slate-700">
                    {token.image ? (
                       <img src={token.image} alt={token.ticker} className="w-full h-full object-cover" />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-slate-600 font-bold text-xs">IMG</div>
                    )}
                </div>

                {/* Info Column */}
                <div className="flex flex-col gap-1 min-w-0">
                    {/* Row 1: Name + Ticker */}
                    <div className="flex items-baseline gap-2">
                        <h3 className="font-bold text-slate-100 text-sm truncate max-w-[150px]">{token.ticker}</h3>
                        <span className="text-xs text-slate-500 font-medium truncate">{token.name}</span>
                        <Copy className="w-3 h-3 text-slate-600 cursor-pointer hover:text-slate-300" />
                    </div>

                    {/* Row 2: Metadata Badges */}
                    <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap">
                        {/* Age */}
                        <span className="text-green-400 font-bold shrink-0" suppressHydrationWarning>{timeAgo(token.created_at)}</span>
                        
                        {/* Socials */}
                        <div className="flex items-center gap-1.5 text-slate-500 shrink-0">
                            {token.website && <Globe className="w-3 h-3 hover:text-blue-400 cursor-pointer" />}
                            {token.twitter && <Twitter className="w-3 h-3 hover:text-blue-400 cursor-pointer" />}
                            {token.telegram && <Send className="w-3 h-3 hover:text-blue-400 cursor-pointer" />}
                        </div>
                        
                        {/* Metrics Row */}
                        <div className="flex items-center gap-3 shrink-0">
                            <div className="flex items-center gap-1" title="Holders">
                                <Users className="w-3 h-3 text-slate-500" />
                                <span>{token.holders}</span>
                            </div>
                            <div className="flex items-center gap-1" title="Pro Traders">
                                <Zap className="w-3 h-3 text-amber-500" />
                                <span>{token.pro_traders_count}</span>
                            </div>
                            <div className="flex items-center gap-1" title="KOLs">
                                <Trophy className="w-3 h-3 text-purple-400" />
                                <span>{token.famous_kols}</span>
                            </div>
                             <div className="flex items-center gap-1 text-[10px] bg-slate-800/50 px-1 rounded" title="Migrations / Created">
                                <Crown className="w-3 h-3 text-yellow-400" /> 
                                <span className="text-blue-400">{token.dev_tokens_migrated}</span>
                                <span className="text-slate-600">/</span>
                                <span className="text-slate-400">{token.dev_tokens_created}</span>
                            </div>
                            <div className="flex items-center gap-1" title="Watching">
                                <Eye className="w-3 h-3 text-cyan-400" /> 
                                <span>{token.active_users_watching}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT: Financials */}
            <div className="flex flex-col items-end gap-0.5 shrink-0 text-right">
                {/* Row 1: MC & Vol */}
                <div className="flex items-center gap-3 text-md">
                    <div className="flex items-center gap-1 text-blue-400">
                        <span className="text-slate-500 text-[12px] mr-0.5">VOL</span>
                        <span className="font-bold">{formatValueInUSD(token.volume_total, solPrice)}</span>
                        {/* <span className="font-bold">{formatValueInSOL(token.volume_total)}</span> */}
                        {/* <TokenSOL variant="branded" size={14} className="shrink-0" /> */}
                    </div>
                    <div className="flex items-center gap-1 text-slate-200">
                        <span className="text-slate-500 text-[12px] mr-0.5">MC</span>
                        <span className="font-bold">{formatValueInUSD(token.market_cap, solPrice)}</span>
                        {/* <span className="font-bold">{formatValueInSOL(token.market_cap)}</span> */}
                        {/* <TokenSOL variant="branded" size={14} className="shrink-0" /> */}
                    </div>
                </div>
                {/* Row 2: Fees & Txns */}
                <div className="flex items-center gap-3 text-xs mb-1">
                    <div className="flex items-center gap-1 text-cyan-400">
                         <span className="text-slate-500 text-[10px] mr-0.5">FEES</span>
                         <span className="font-mono">{token.fees_paid ? formatValueInSOL(token.fees_paid) : "0"}</span>
                         <TokenSOL variant="branded" size={12} className="shrink-0" />
                    </div>
                    <div>
                         <span className="text-slate-500 mr-1 text-[10px]">TX</span>
                         <span className="font-mono text-slate-300">{token.txns_total}</span>
                    </div>
                </div>
                
                 <button className="bg-amber-600 hover:bg-amber-500 text-black text-[10px] font-bold px-3 py-1 rounded transition-colors flex items-center gap-1 mt-auto">
                     <Zap className="w-3 h-3 fill-black" /> 0 SOL
                 </button>
            </div>
        </div>

        {/* LOWER SECTION: Risk Percentages */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-800/50 flex-wrap">
            <MetricBadge label="TOP10" value={`${token.top10_holders_percent.toFixed(0)}%`} color={token.top10_holders_percent > 30 ? "red" : "green"} />
            <MetricBadge label="DEV" value={`${token.dev_holding_percent.toFixed(0)}%`} color={token.dev_holding_percent > 10 ? "red" : "green"} />
            <MetricBadge label="SNIPER" value={`${token.snipers_percent.toFixed(0)}%`} color={token.snipers_percent > 50 ? "red" : "amber"} icon={Zap} />
            <MetricBadge label="INSIDER" value={`${token.insiders_percent.toFixed(0)}%`} color="purple" />
            <MetricBadge label="BUNDLES" value={`${token.bundled_percent?.toFixed(0) || 0}%`} color="blue" />
        </div>
        
        {/* Debug Panel: Collapsed by default */}
        <DebugFieldsPanel token={token} />
    </div>
  );
});
