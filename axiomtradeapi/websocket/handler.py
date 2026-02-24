"""
Message handling for WebSocket client
"""
import json
import logging
from typing import Dict, Callable, Optional
import websockets
import msgpack

# Only import if needed types are not available by default or string forward references are tricky
# For mixins, using loose coupling is okay.

class MessageHandlerMixin:
    """Message handling for WebSocket client"""
    
    # Type hinting for dependencies
    logger: logging.Logger
    ws: Optional[websockets.WebSocketClientProtocol]
    _callbacks: Dict[str, Callable]
    _pulse_message_count: int
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            # If self.ws is None, we can't iterate. But start() ensures connection.
            if not self.ws:
                self.logger.error("WebSocket is not connected (ws is None)")
                return

            async for message in self.ws:
                try:
                    # Handle binary messages (Pulse WebSocket uses MessagePack)
                    if isinstance(message, bytes):
                        self._pulse_message_count += 1
                        self.logger.debug(f"Received Pulse message #{self._pulse_message_count} ({len(message)} bytes)")
                        
                        # Call callback if registered
                        if "pulse_message_count" in self._callbacks:
                            try:
                                self._callbacks["pulse_message_count"](self._pulse_message_count)
                            except Exception as e:
                                self.logger.error(f"Error in pulse_message_count callback: {e}")
                        
                        # Parse MessagePack data
                        try:
                            # raw=False ensures strings are decoded from bytes
                            data = msgpack.unpackb(message, raw=False)
                            
                            # Dispatch to pulse data callback if registered
                            if "pulse" in self._callbacks:
                                await self._callbacks["pulse"](data)
                                
                        except Exception as e:
                            self.logger.error(f"Failed to unpack Pulse message: {e}")
                        
                        continue
                    
                    # Handle text messages (JSON format)
                    data = json.loads(message)
                    
                    # Handle new token updates
                    if "new_pairs" in self._callbacks and data.get("room") == "new_pairs":
                        content = data.get("content")
                        if content:
                            # Wrap single token in array for callback compatibility
                            await self._callbacks["new_pairs"]([content])
                    
                    # Handle SOL price updates
                    if "sol_price" in self._callbacks and data.get("room") == "sol_price":
                        content = data.get("content")
                        if content is not None:
                            # content should be a float value like 116.425
                            await self._callbacks["sol_price"](float(content))
                    
                    # Handle token price updates
                    for key, callback in self._callbacks.items():
                        if key.startswith("token_price_"):
                            # Extract token from callback key
                            token = key.replace("token_price_", "")
                            # Check if room matches the token
                            if data.get("room") == token and data.get("content"):
                                await callback(data.get("content"))
                            
                    # Handle wallet transactions
                    for key, callback in self._callbacks.items():
                        if key.startswith("wallet_transactions_"):
                            # Extract wallet address from callback key
                            wallet_address = key.replace("wallet_transactions_", "")
                            # Check if room matches the expected format for this wallet
                            if data.get("room") == f"v:{wallet_address}" and data.get("content"):
                                await callback(data.get("content"))
                    
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse WebSocket message: {message}")
                except Exception as e:
                    self.logger.error(f"Error handling WebSocket message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"WebSocket message handler error: {e}")
