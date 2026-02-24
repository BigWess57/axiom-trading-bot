"use client";

import { useEffect, useState, useRef } from "react";
import { socket } from "@/lib/socket"; // Use singleton
import { PulseToken, TokenRemovedEvent } from "@/lib/types";

export type TokensByCategory = {
  newPairs: PulseToken[];
  finalStretch: PulseToken[];
  migrated: PulseToken[];
};

export function usePulseSocket() {
  const [tokensByCategory, setTokensByCategory] = useState<TokensByCategory>({
    newPairs: [],
    finalStretch: [],
    migrated: []
  });
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  
  const [solPrice, setSolPrice] = useState<number | null>(null);
  
  // No need for socketRef, we use the imported singleton
  const tokensMapRef = useRef<Map<string, PulseToken>>(new Map()); // Use Map for faster lookups

  // Helper to organize tokens by category
  const organizeByCategory = (tokensMap: Map<string, PulseToken>): TokensByCategory => {
    const organized: TokensByCategory = {
      newPairs: [],
      finalStretch: [],
      migrated: []
    };
    tokensMap.forEach(token => {
      const category = token.category as keyof TokensByCategory;
      if (category && organized[category]) {
        organized[category].push(token);
      }
    });
    // Sort each category by created_at (newest first)
    const sortTokens = (tokens: PulseToken[]) => {
      return tokens.sort((a, b) => {
        if (!a.created_at) return 1;
        if (!b.created_at) return -1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
    };

    organized.newPairs = sortTokens(organized.newPairs);
    organized.finalStretch = sortTokens(organized.finalStretch);
    organized.migrated = sortTokens(organized.migrated);
    return organized;
  };

  // Helper to update state
  const updateTokens = () => {
    const organized = organizeByCategory(tokensMapRef.current);
    setTokensByCategory(organized);
    setLastUpdate(new Date());
  };

  useEffect(() => {
    function onConnect() {
      console.log("Connected to Pulse Backend");
      setIsConnected(true);
    }

    function onDisconnect() {
      console.log("Disconnected from Pulse Backend");
      setIsConnected(false);
    }

    function onSnapshot(data: PulseToken[]) {
      console.log("Received Snapshot:", data.length, "tokens");
      tokensMapRef.current.clear();
      data.forEach(token => tokensMapRef.current.set(token.pair_address, token));
      updateTokens();
    }

    function onNewToken(newToken: PulseToken) {
      console.log("New Token:", newToken.ticker, "Category:", newToken.category);
      tokensMapRef.current.set(newToken.pair_address, newToken);
      updateTokens();
    }

    function onTokenUpdate(updatedToken: PulseToken) {
      if (tokensMapRef.current.has(updatedToken.pair_address)) {
        tokensMapRef.current.set(updatedToken.pair_address, updatedToken);
        updateTokens();
      }
    }

    function onTokenRemoved(event: TokenRemovedEvent) {
      console.log("Token Removed:", event.pair_address);
      tokensMapRef.current.delete(event.pair_address);
      updateTokens();
    }

    function onSolPrice(data: { price: number; timestamp: string }) {
      setSolPrice(data.price);
    }

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("snapshot", onSnapshot);
    socket.on("new_token", onNewToken);
    socket.on("token_update", onTokenUpdate);
    socket.on("token_removed", onTokenRemoved);
    socket.on("sol_price", onSolPrice);

    if (socket.connected) {
      setIsConnected(true);
      // Request snapshot since we might have missed the 'connect' event
      socket.emit('request_snapshot');
    }

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("snapshot", onSnapshot);
      socket.off("new_token", onNewToken);
      socket.off("token_update", onTokenUpdate);
      socket.off("token_removed", onTokenRemoved);
      socket.off("sol_price", onSolPrice);
    };
  }, []);

  return { tokensByCategory, isConnected, lastUpdate, solPrice };
}
