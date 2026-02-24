import { CandlestickData, CandlestickSeries, ColorType, createChart, createSeriesMarkers, IChartApi, ISeriesApi, SeriesMarker, Time } from 'lightweight-charts';
import { useEffect, useRef } from 'react';
import { TokenState, TradeResult } from '../lib/types';

interface UseTradingViewChartProps {
    data: CandlestickData[];
    tokenState?: TokenState | null; // Allow null
    height?: number;
    containerRef: React.RefObject<HTMLDivElement|null>;
}

export const useTradingViewChart = ({
    data,
    tokenState,
    height = 400,
    containerRef
}: UseTradingViewChartProps) => {
    const chartRef = useRef<IChartApi | null>(null);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const markersPrimitiveRef = useRef<any>(null);

    // 1. Chart Setup & Series Creation
    useEffect(() => {
        if (!containerRef.current) return;

        const chart = createChart(containerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#D1D5DB',
            },
            grid: {
                vertLines: { color: 'rgba(55, 65, 81, 0.4)' },
                horzLines: { color: 'rgba(55, 65, 81, 0.4)' },
            },
            width: containerRef.current.clientWidth,
            height: height,
            timeScale: {
                timeVisible: true,
                secondsVisible: true,
                borderColor: '#4B5563',
            },
            rightPriceScale: {
                borderColor: '#4B5563',
                autoScale: true,
            },
        });

        chartRef.current = chart;

        // 2. Create Series
        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            priceFormat: {
                type: 'custom',
                formatter: (price: number) => {
                    if (price >= 1000000) return (price / 1000000).toFixed(2) + 'M';
                    if (price >= 1000) return (price / 1000).toFixed(1) + 'K';
                    return price.toFixed(2);
                },
                minMove: 0.01,
            },
        });

        seriesRef.current = candleSeries;

        // Initial Data Set
        if (data.length > 0) {
            candleSeries.setData(data);
            chart.timeScale().fitContent();
        }

        const handleResize = () => {
            if (containerRef.current) {
                chart.applyOptions({ width: containerRef.current.clientWidth });
            }
        };

        const resizeObserver = new ResizeObserver(handleResize);
        resizeObserver.observe(containerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
            chartRef.current = null;
            seriesRef.current = null;
            markersPrimitiveRef.current = null;
        };
    }, [height]); // Re-run if height changes

    // 3. Update Data (When data changes)
    useEffect(() => {
        if (seriesRef.current && data.length > 0) {
            seriesRef.current.setData(data);
            // Optional: Only fit content on initial load, not every update to avoid jumping
            // chartRef.current?.timeScale().fitContent(); 
        }
    }, [data]);

    // 4. Update Markers (When tokenState changes)
    useEffect(() => {
        if (!seriesRef.current) return;

        // Helper to convert trade time to chart time
        const toChartTime = (t: string | number): Time => {
            const date = new Date(t);
            return Math.ceil(date.getTime() / 1000) as Time;
        };

        const formatMC = (val?: number) => {
            if (!val) return '0';
            if (val >= 1000000) return (val / 1000000).toFixed(2) + 'M';
            if (val >= 1000) return (val / 1000).toFixed(1) + 'K';
            return val.toFixed(2);
        };

        const markers: SeriesMarker<Time>[] = [];

        if (tokenState?.active_trade) {
            markers.push({
                time: toChartTime(tokenState.active_trade.time_bought),
                position: 'aboveBar',
                color: '#00FFFF',
                shape: 'circle',
                size: 5,
                text: 'Buy at ' + formatMC(tokenState.active_trade.entry_mc),
            });
        }

        if (tokenState?.past_trades) {
            tokenState.past_trades.forEach((trade: TradeResult) => {
                markers.push({
                    time: toChartTime(trade.time_bought),
                    position: 'aboveBar',
                    color: '#00FFFF',
                    shape: 'circle',
                    size: 5,
                    text: 'Buy at ' + formatMC(trade.buy_market_cap),
                });
                if (trade.time_sold) {
                    markers.push({
                        time: toChartTime(trade.time_sold),
                        position: 'aboveBar',
                        color: '#FF3131',
                        shape: 'circle',
                        size: 5,
                        text: 'Sell at ' + formatMC(trade.sell_market_cap),
                    });
                }
            });
        }

        // Sort markers by time (required by library)
        markers.sort((a, b) => (a.time as number) - (b.time as number));

        if (!markersPrimitiveRef.current) {
            markersPrimitiveRef.current = createSeriesMarkers(seriesRef.current, markers);
        } else {
            markersPrimitiveRef.current.setMarkers(markers);
        }

    }, [tokenState]);

    return {};
};
