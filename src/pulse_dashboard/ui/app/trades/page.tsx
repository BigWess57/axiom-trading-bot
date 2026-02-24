"use client";

import { useTradeData } from '@/hooks/useTradeData';
import { motion, AnimatePresence } from 'framer-motion';
import TradeCard from '@/components/TradeCard';
import StatCard from '@/components/StatCard';
import TokenSOL from '@web3icons/react/icons/tokens/TokenSOL';

export default function TradesPage() {
  const { botState, isConnected, solPrice } = useTradeData();

  if (!botState) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-64px)]">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Waiting for Bot Data...</h2>
          <p className="text-gray-400">Ensure your trading bot is running.</p>
        </div>
      </div>
    );
  }

  const { stats, active_trades, recent_trades } = botState;

  return (
    <div className="max-w-8xl mx-auto px-4 sm:px-6 lg:px-10 py-8 space-y-8">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Current Balance" value={`${stats.balance.toFixed(3)}`} isSol />
        <StatCard 
          title="Total P&L (fees included)" 
          value={`${stats.total_profit > 0 ? '+' : ''}${stats.total_profit.toFixed(3)}`} 
          valueColor={stats.total_profit > 0 ? 'text-green-400' : 'text-red-400'}
          isSol
        />
        <StatCard title="Win Rate" value={`${stats.win_rate.toFixed(1)}%`} />
        <StatCard title="Total Trades" value={stats.total_trades.toString()} />
        <StatCard title="Fees Paid" value={`${stats.total_fees_paid.toFixed(3)}`} valueColor="text-red-400" isSol />
      </div>

      {/* Active Trades Section */}
      <div>
        <h2 className="text-2xl font-bold mb-4 flex items-center">
          Active Trades 
          <span className="ml-3 px-2 py-1 bg-blue-900/30 text-blue-400 text-sm rounded-full">
            {active_trades.length}
          </span>
        </h2>
        
        {active_trades.length === 0 ? (
          <div className="text-center py-12 bg-gray-900/20 rounded-xl border border-dashed border-gray-800">
            <p className="text-gray-500">No active trades currently open.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {active_trades.map((trade) => (
                <TradeCard 
                  key={trade.token.pair_address} 
                  trade={trade} 
                  solPrice={solPrice}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Recent History Table */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Recent History</h2>
        <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900/20">
          <table className="min-w-full divide-y divide-gray-800">
            <thead className="bg-gray-900/50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Token</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Pair Address</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Profit (fees included)</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Time Sold</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Sell Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {recent_trades.slice(0, 15).map((trade, idx) => (
                <tr 
                  key={idx} 
                  onClick={() => window.location.href = `/trades/${trade.pair_address}`}
                  className="hover:bg-gray-800/30 transition-colors cursor-pointer"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    <div className="font-mono">{trade.token_ticker}</div> <div className="text-gray-500">{trade.token_name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {trade.pair_address.substring(0, 8)}...
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-mono ${trade.profit > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    <div className="flex items-center justify-end gap-1">{trade.profit > 0 ? '+' : ''}{trade.profit.toFixed(4)}<TokenSOL variant="branded" size={14} className="shrink-0" /></div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    {new Date(trade.time_sold).toLocaleTimeString()}
                  </td>
                  {trade.sell_reason &&
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                    <span className="text-gray-300 font-bold">{trade.sell_reason.category}</span> - <span className="text-gray-400">{trade.sell_reason.details}</span>
                  </td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}



