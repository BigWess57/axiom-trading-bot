import React, { useRef } from 'react';
import { TokenState } from '@/utils/types';
import { useTradingViewChart } from '../hooks/useTradingViewChart';
import { CandlestickData } from 'lightweight-charts';

interface TradingViewChartProps {
  data: CandlestickData[];
  tokenState?: TokenState | null;
  height?: number;
  loading?: boolean;
  error?: string | null;
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({ 
  data,
  tokenState, 
  height = 400,
  loading = false,
  error = null
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  
  useTradingViewChart({
      data,
      tokenState,
      height,
      containerRef: chartContainerRef
  });

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={chartContainerRef} className="w-full h-full" />
      <div className="absolute top-2 left-2 z-10 px-2 py-1 rounded bg-gray-800/60 backdrop-blur text-xs font-medium text-gray-300 border border-gray-700">
            1s
        </div>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm z-10">
          <span className="loading loading-spinner loading-lg text-primary"></span>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
          <div className="text-error font-medium">{error}</div>
        </div>
      )}
    </div>
  );
};

export default TradingViewChart;
