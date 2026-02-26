"use client";

import { useEffect, useState } from 'react';
import { socket } from '@/utils/socket';
import { BotState } from '@/utils/types';

export function useTradeData() {
  const [botState, setBotState] = useState<BotState | null>(null);
  const [solPrice, setSolPrice] = useState<number | null>(null);
  const [isConnected, setIsConnected] = useState(socket.connected);

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
    }

    function onDisconnect() {
      setIsConnected(false);
    }

    function onBotStateUpdate(data: BotState) {
      setBotState(data);
    }

    function onSolPrice(data: { price: number; timestamp: string }) {
      setSolPrice(data.price);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('bot_state_update', onBotStateUpdate);
    socket.on('sol_price', onSolPrice);

    // If socket is already connected when hook mounts
    if (socket.connected) {
      setIsConnected(true);
    }

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('bot_state_update', onBotStateUpdate);
      socket.off('sol_price', onSolPrice);
    };
  }, []);

  return { 
    botState, 
    solPrice, 
    isConnected,
    socket // Expose socket in case components need ad-hoc listeners (e.g. token_update)
  };
}
