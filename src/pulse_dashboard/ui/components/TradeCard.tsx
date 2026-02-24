import { motion } from 'framer-motion';

import Link from 'next/link';
import { TradeInfo } from '@/lib/types';
import { BarChart2 } from 'lucide-react';

function TradeCard({ trade, solPrice }: { trade: TradeInfo, solPrice: number | null }) {
  const isProfit = trade.pnl_pct >= 0;

  const age_seconds = (new Date().getTime() - new Date(trade.time_bought).getTime()) / 1000;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className={`bg-gray-800/50 backdrop-blur border ${isProfit ? 'border-green-500/20' : 'border-red-500/20'} rounded-xl overflow-hidden transition-all duration-300`}
    >
      <div className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-bold text-white leading-none">{trade.token.ticker} <span className="text-xs text-gray-500">{trade.token.name}</span></h3>
            <p className="text-xs text-gray-500 mt-1 font-mono ">{trade.token.pair_address.substring(0, 6)}...{trade.token.pair_address.substring(trade.token.pair_address.length - 4)}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`px-2 py-1 rounded text-xs font-bold ${isProfit ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-500'}`}>
              {isProfit ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
            </div>
            <Link href={`/trades/${trade.token.pair_address}`} className="p-1 hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-white" title="View Chart">
                <BarChart2 size={18} />
            </Link>
          </div>
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Entry MC</span>
            <span className="font-mono text-gray-200">${Math.round(trade.entry_mc).toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Current MC</span>
            <span className="font-mono text-gray-200">${Math.round(trade.token.market_cap * (solPrice || 0)).toLocaleString()}</span>
          </div>
          <div className="flex justify-between pt-2 border-t border-gray-800">
            <span className="text-gray-400">P&L (SOL)</span>
            <span className={`font-mono font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
              {isProfit ? '+' : ''}{trade.pnl_absolute.toFixed(4)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Holding Time</span>
            <span className="font-mono text-gray-500">
              {Math.floor(age_seconds / 60)}:{Math.floor(age_seconds % 60).toString().padStart(2, '0')}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default TradeCard