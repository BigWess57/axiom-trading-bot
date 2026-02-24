import json
import logging
import websockets
from typing import Dict, Callable, Optional, Any
from .types import WebSocketMode

class SubscriptionMixin:
    """Subscription management for WebSocket client"""
    
    # Type hinting for dependencies
    logger: logging.Logger
    ws: Optional[websockets.WebSocketClientProtocol]
    _callbacks: Dict[str, Callable]
    _pulse_message_count: int
    
    async def connect(self, mode: WebSocketMode = WebSocketMode.NEW_PAIRS) -> bool:
        """From ConnectionMixin"""
        raise NotImplementedError
        
    async def subscribe_new_tokens(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to new token updates."""
        if not self.ws:
            if not await self.connect(mode=WebSocketMode.NEW_PAIRS):
                return False

        self._callbacks["new_pairs"] = callback
        
        try:
            await self.ws.send(json.dumps({
                "action": "join",
                "room": "new_pairs"
            }))
            self.logger.info("Subscribed to new token updates")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to new tokens: {e}")
            return False

    async def subscribe_token_price(self, token: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to token price updates."""
        if not self.ws:
            if not await self.connect(mode=WebSocketMode.TOKEN_PRICE):
                return False

        self._callbacks[f"token_price_{token}"] = callback
        
        try:
            await self.ws.send(json.dumps({
                "action": "join",
                "room": token
            }))
            self.logger.info(f"Subscribed to token price updates for {token}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to token price: {e}")
            return False

    async def unsubscribe_token_price(self, token: str):
        """Unsubscribe from token price updates."""
        if not self.ws:
            return False

        # Remove callback
        self._callbacks.pop(f"token_price_{token}", None)
        
        try:
            await self.ws.send(json.dumps({
                "action": "leave",
                "room": token
            }))
            self.logger.info(f"Unsubscribed from token price updates for {token}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from token price: {e}")
            return False
        
    async def subscribe_wallet_transactions(self, wallet_address: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to wallet transaction updates."""
        if not self.ws:
            if not await self.connect(mode=WebSocketMode.NEW_PAIRS):
                return False

        self._callbacks[f"wallet_transactions_{wallet_address}"] = callback
        
        try:
            await self.ws.send(json.dumps({
                "action": "join",
                "room": f"v:{wallet_address}"
            }))
            self.logger.info(f"Subscribed to wallet transactions for {wallet_address}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to wallet transactions: {e}")
            return False

    async def subscribe_to_pulse(self, filters: Optional[Dict[str, Any]] = None, count_callback: Optional[Callable[[int], None]] = None, data_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Subscribe to Pulse WebSocket feed for real-time token tracking.
        
        Connects to the Pulse WebSocket endpoint and subscribes to newPairs, finalStretch, and migrated categories.
        
        Args:
            filters: Optional dict with filter configuration for newPairs, finalStretch, and migrated.
                    If None, subscribes to all categories without filters.
            callback: Optional callback function that receives message count updates (int).
            data_callback: Optional callback function that receives the decoded data (dict/list).
        
        Returns:
            True if subscription successful, False otherwise
        """
        # Connect to Pulse WebSocket
        if not self.ws or getattr(self.ws, "close_code", None) is not None:
            if not await self.connect(mode=WebSocketMode.PULSE):
                self.logger.error("Failed to connect to Pulse WebSocket")
                return False
        
        # Build subscription message
        subscription_msg = {
            "type": "userState",
            "state": {
                "tables": {
                    "newPairs": True,
                    "finalStretch": True,
                    "migrated": True
                },
                "filters": filters or {},
                "blacklist": {},
                "pausedPairs": {
                    "newPairs": [],
                    "finalStretch": [],
                    "migrated": []
                },
                "showHiddenPulseTokens": False,
                "unhideMigrated": False
            }
        }
        
        try:
            # Send subscription message
            await self.ws.send(json.dumps(subscription_msg))
            self.logger.info("Subscribed to Pulse feed (newPairs, finalStretch, migrated)")
            
            # Store callback for message counting
            if count_callback:
                self._callbacks["pulse_message_count"] = count_callback
                
            # Store callback for actual data processing
            if data_callback:
                self._callbacks["pulse"] = data_callback
            
            # Reset message counter
            self._pulse_message_count = 0
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to Pulse: {e}")
            return False
    
    async def subscribe_sol_price(self, callback: Callable[[float], None]):
        """Subscribe to SOL price updates."""
        if not self.ws:
            if not await self.connect(mode=WebSocketMode.SOL_PRICE):
                return False

        self._callbacks["sol_price"] = callback
        
        try:
            await self.ws.send(json.dumps({
                "action": "join",
                "room": "sol_price"
            }))
            self.logger.info("Subscribed to SOL price updates")
            return True
        except Exception as e:
            self.logger.error(f"Failed to subscribe to SOL price: {e}")
            return False

    def get_pulse_message_count(self) -> int:
        """Get the current count of Pulse messages received.
        
        Returns:
            Total number of messages received since subscription
        """
        return self._pulse_message_count
