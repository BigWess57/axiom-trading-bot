"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { TokenState } from '@/lib/types';
import TradingViewChart from '@/components/TradingViewChart';
import { useTradeData } from '@/hooks/useTradeData';
import { useCandleData } from '@/hooks/useCandleData';

export default function TradeChartPage() {
  const params = useParams();
  const pairAddress = params.pairAddress as string;
  
  const { botState, isConnected, socket } = useTradeData();
  const [tokenState, setTokenState] = useState<TokenState | null>(null);

  const calculateProfit = (state: TokenState) => {
    return state.past_trades.reduce((acc, t) => acc + t.profit, 0) + (state.active_trade ? state.active_trade.pnl_absolute : 0);
  };

  // Derive TokenState when botState updates
  useEffect(() => {
    if (!botState || !pairAddress) return;

    const activeTrade = botState.active_trades.find(t => t.token.pair_address === pairAddress);
    const pastTrades = botState.recent_trades.filter(t => t.pair_address === pairAddress);
    
    // We need a base token info. If active trade exists, use it.
    // If only past trades, use the first one.
    const refTrade = activeTrade || pastTrades[0];
    
    if (refTrade) {
         // Helper to extract common fields whether it's active or past trade
        const isActive = 'token' in refTrade;
        const ticker = isActive ? refTrade.token.ticker : refTrade.token_ticker;
        const name = isActive ? refTrade.token.name : refTrade.token_name;
        const pAddr = isActive ? refTrade.token.pair_address : refTrade.pair_address;
        const mCap = isActive ? refTrade.token.market_cap : 0; 
        
        // For Active Trades, we have supply. For Past Trades, we rely on the chart to fetch it bundled.
        // We set 0 here for past trades, which is fine because the chart handles scaling itself now.
        const supply = isActive ? refTrade.token.total_supply : 0;

        const state: TokenState = {
            token: isActive ? { ...refTrade.token } : {
                pair_address: pAddr,
                name: name,
                ticker: ticker, 
                market_cap: mCap,
                total_supply: supply,
                //All this not needed for now
                token_address: "", creator: "",  image: null, chain_id: 101, protocol: null,
                website: null, twitter: null, telegram: null, creator_name: null,
                top10_holders_percent: 0, dev_holding_percent: 0, snipers_percent: 0,
                insiders_percent: 0, bundled_percent: 0, holders: 0, volume_total: 0,
                fees_paid: 0, txns_total: 0, buys_total: 0, sells_total: 0,
                pro_traders_count: 0, migrated_at: null, created_at: null,
                dev_tokens_migrated: 0, dev_tokens_created: 0, famous_kols: 0,
                active_users_watching: 0, twitter_followers: 0, category: null
             },
             active_trade: activeTrade,
             past_trades: pastTrades
         };
        setTokenState(state);
    }

    }, [botState, pairAddress]);

    const { age, candles, loading: chartLoading, error: chartError } = useCandleData({ 
        pairAddress, 
        tokenState 
    });

    const timeAgo = (date: Date | null) => {
        if (!date) return "";
        const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h`;
    };

  if (!pairAddress) return <div className="p-10 text-center">Invalid Pair Address</div>;

  return (
    <div className="max-w-8xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-64px)] flex flex-col">
      <div className="mb-4 flex items-center gap-4">
        <Link href="/trades" className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            {tokenState?.token.ticker || "Loading..."} 
            <span className="text-gray-500 text-sm">{tokenState?.token.name}</span>
            {tokenState?.active_trade && (
                <div className="flex items-center gap-2">
               <div className="relative flex h-3 w-3 ml-2" title="Active Trade">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
               </div>
               <span className="text-green-600 text-sm">Active Trade</span>
               </div>
            )}
          </h1>
          <p className="text-xs text-gray-500 font-mono flex items-center gap-3">
            <span>{pairAddress}</span>
            {tokenState && (
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                    {tokenState.past_trades.length} recent trades
                    </span>
                )}
          </p>
          <div className="text-md text-green-500 font-mono flex items-center gap-3">
            <span>{timeAgo(age)}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-gray-900/40 backdrop-blur border border-gray-700 rounded-xl overflow-hidden shadow-xl flex flex-col">
        <div className="p-4 border-b border-gray-700 bg-gray-800/20 flex justify-between items-center">
            <h2 className="font-semibold text-gray-300">Live Chart</h2>
            {/* Future: Add timeframe selectors here */}
        </div>
        <div className="flex-1 relative">
             {/* Using a key to force re-mount if pair changes, though redundant with useEffect deps */}
             <TradingViewChart 
                key={pairAddress}
                data={candles}
                tokenState={tokenState} 
                height={500} 
                loading={chartLoading}
                error={chartError}
             />
        </div>
      </div>
      
       {/* Debug / Info Section below chart could go here */}
       {tokenState && (
           <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
               <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
                   <div className="text-gray-500 text-xs uppercase mb-1">Total Trades</div>
                   <div className="text-xl font-mono">{tokenState.past_trades.length + (tokenState.active_trade ? 1 : 0)}</div>
               </div>
               <div className="p-4 bg-gray-800/30 rounded-lg border border-gray-700">
                    <div className="text-gray-500 text-xs uppercase mb-1">Realized P&L</div>
                    <div className={`text-xl font-mono ${calculateProfit(tokenState) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {calculateProfit(tokenState).toFixed(4)} SOL
                    </div>
               </div>
           </div>
       )}
    </div>
  );
}
