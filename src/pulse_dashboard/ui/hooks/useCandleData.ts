import { Time, CandlestickData } from 'lightweight-charts';
import { useEffect, useState, useRef } from 'react';
import { socket } from '@/lib/socket';
import { TokenState } from '../lib/types';

interface UseCandleDataProps {
    pairAddress: string;
    tokenState?: TokenState | null;
}

export const useCandleData = ({ pairAddress, tokenState }: UseCandleDataProps) => {
    const [candles, setCandles] = useState<CandlestickData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const supplyRef = useRef(1_000_000_000);
    const [age, setAge] = useState<Date>(new Date());

    // Update supply ref when tokenState changes
    useEffect(() => {
        if (tokenState?.token?.total_supply) {
            supplyRef.current = tokenState.token.total_supply;
        }
    }, [tokenState]);

    // 1. Fetch Historical Data
    useEffect(() => {
        let mounted = true;
        const fetchCandles = async () => {
            if (!pairAddress) return;
            
            try {
                setLoading(true);
                const res = await fetch(`http://localhost:8000/api/candles/${pairAddress}`);
                const data = await res.json();

                if (data.error) throw new Error(data.error);

                // Handle response format
                let rawCandles = [];
                if (data.candles && data.candles.bars) {
                    rawCandles = data.candles.bars;
                } else {
                    rawCandles = Array.isArray(data) ? data : (data.candles || data.bars || []);
                }

                const tokenInfo = data.token_info || {};
                if (tokenInfo.created_at) {
                    setAge(new Date(tokenInfo.created_at));
                }
                // Use supply from API response first, then fallback to tokenState (active trades), then default
                const supply = tokenInfo.total_supply || tokenState?.token?.total_supply || 1_000_000_000;
                
                // Update ref if we got it from API
                if (tokenInfo.total_supply) {
                    supplyRef.current = tokenInfo.total_supply;
                }

                let candleData = rawCandles.map((c: any) => {
                    // v2 format: [time, open, high, low, close, volume]
                    if (Array.isArray(c)) {
                        return {
                            time: c[0] / 1000 as Time,
                            open: c[1] * supply,
                            high: c[2] * supply,
                            low: c[3] * supply,
                            close: c[4] * supply,
                        }
                    }
                    // v1 format: object
                    return {
                        time: c.time / 1000 as Time,
                        open: c.open * supply,
                        high: c.high * supply,
                        low: c.low * supply,
                        close: c.close * supply,
                    };
                });

                // Sort by time
                candleData.sort((a: any, b: any) => (a.time as number) - (b.time as number));

                if (mounted) {
                    setCandles(candleData);
                    setLoading(false);
                }
            } catch (err: any) {
                if (mounted) {
                    console.error("Failed to fetch candles", err);
                    setLoading(false);
                    setError(err.message);
                }
            }
        };

        fetchCandles();
        return () => { mounted = false; };
    }, [pairAddress]); // Only re-fetch if pairAddress changes

    // 2. Real-time Price Updates via WebSocket
    useEffect(() => {
        if (!pairAddress) return;

        console.log("Subscribing to price updates for", pairAddress);
        socket.emit('subscribe_price', pairAddress);

        const handlePriceUpdate = (data: any) => {
            // Assuming data structure { price_usd: number, timestamp: number }
            const time = Math.floor((data.timestamp || Date.now()) / 1000) as Time;
            const rawPrice = data.price_usd;
            const currentSupply = supplyRef.current;

            if (rawPrice && currentSupply) {
                const mCapPrice = rawPrice * currentSupply;

                setCandles(prevCandles => {
                    if (prevCandles.length === 0) return prevCandles;

                    const lastCandle = prevCandles[prevCandles.length - 1];
                    const newCandles = [...prevCandles];

                    // Check if we are updating the current bar or starting a new one
                    if ((lastCandle.time as number) === (time as number)) {
                        // Update existing candle
                        const updatedCandle = {
                            ...lastCandle,
                            high: Math.max(lastCandle.high, mCapPrice),
                            low: Math.min(lastCandle.low, mCapPrice),
                            close: mCapPrice
                        };
                        newCandles[newCandles.length - 1] = updatedCandle;
                    } else {
                        // New candle
                        const newCandle = {
                            time: time,
                            open: lastCandle.close,
                            high: Math.max(lastCandle.close, mCapPrice),
                            low: Math.min(lastCandle.close, mCapPrice),
                            close: mCapPrice
                        };
                        newCandles.push(newCandle);
                    }
                    return newCandles;
                });
            }
        };

        socket.on('price_update', handlePriceUpdate);

        return () => {
            console.log("Unsubscribing from price updates for", pairAddress);
            socket.emit('unsubscribe_price', pairAddress);
            socket.off('price_update', handlePriceUpdate);
        };
    }, [pairAddress]);

    return { age, candles, loading, error };
};
