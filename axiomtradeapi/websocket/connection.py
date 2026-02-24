import logging
import inspect
import websockets
from typing import Optional, Dict, TYPE_CHECKING
from ..content.endpoints import BaseUrls, Websockets
from .types import WebSocketMode

if TYPE_CHECKING:
    from ..auth.auth_manager import AuthManager

class ConnectionMixin:
    """Connection management for WebSocket client"""
    
    # Type hinting for dependencies
    auth_manager: 'AuthManager'
    logger: logging.Logger
    ws: Optional[websockets.WebSocketClientProtocol]
    ws_url: str
    ws_url_token_price: str
    _uses_additional_headers: bool
    _uses_extra_headers: bool
    
    async def _connect_with_headers(self, url: str, headers: Dict[str, str], compression: Optional[str] = None):
        """
        Connect to WebSocket with compatibility for different websockets versions.
        Uses additional_headers (websockets 13+) or extra_headers (websockets 10.x) based on detection.
        """
        kwargs = {"compression": compression} if compression else {}
        
        if self._uses_additional_headers:
            return await websockets.connect(url, additional_headers=headers, **kwargs)
        elif self._uses_extra_headers:
            return await websockets.connect(url, extra_headers=headers, **kwargs)
        else:
            # Fallback: try both
            try:
                return await websockets.connect(url, additional_headers=headers, **kwargs)
            except TypeError as e1:
                # Try extra_headers as fallback
                try:
                    self.logger.debug("Fallback: Retrying connection with extra_headers parameter")
                    return await websockets.connect(url, extra_headers=headers, **kwargs)
                except TypeError as e2:
                    # Both failed - raise informative error
                    raise TypeError(
                        f"Failed to connect with both 'additional_headers' and 'extra_headers'. "
                        f"Original error: {e1}. Fallback error: {e2}"
                    ) from e1

    async def connect(self, mode: WebSocketMode = WebSocketMode.NEW_PAIRS) -> bool:
        """Connect to the WebSocket server.
        
        Args:
            mode: WebSocketMode enum specifying which WebSocket to connect to:
                  - NEW_PAIRS: New token pairs feed (default)
                  - TOKEN_PRICE: Token price updates feed
                  - PULSE: Pulse dashboard feed (binary MessagePack)
        """
        # Ensure we have valid authentication
        if not self.auth_manager.ensure_valid_authentication():
            self.logger.error("WebSocket authentication failed - unable to obtain valid tokens")
            self.logger.error("Please login with valid email and password")
            return False
        
        # Get tokens from auth manager
        tokens = self.auth_manager.get_tokens()
        if not tokens:
            self.logger.error("No authentication tokens available")
            return False
        
        headers = {
            'Origin': BaseUrls.AXIOM_TRADE,
            'Cache-Control': 'no-cache',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Pragma': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }
        
        # Add authentication cookies from auth manager
        cookie_header = f"auth-access-token={tokens.access_token}; auth-refresh-token={tokens.refresh_token}"
        headers["Cookie"] = cookie_header
        
        self.logger.debug(f"Connecting to WebSocket with headers: {headers}")
        self.logger.debug(f"Using tokens: access_token length={len(tokens.access_token)}, refresh_token length={len(tokens.refresh_token)}")
        
        try:
            if mode == WebSocketMode.PULSE:
                current_url = Websockets.PULSE
            elif mode == WebSocketMode.TOKEN_PRICE:
                current_url = self.ws_url_token_price
            elif mode == WebSocketMode.SOL_PRICE:
                current_url = self.ws_url  # SOL price uses same cluster as NEW_PAIRS
            else:  # WebSocketMode.NEW_PAIRS
                current_url = self.ws_url
            
            # Try the primary URL first
            self.logger.info(f"Attempting to connect to WebSocket ({mode.value}): {current_url}")
            if mode == WebSocketMode.PULSE:
                # Disable explicit compression param to simplify headers and rely on default negotiation
                self.ws = await self._connect_with_headers(current_url, headers)
            else:
                self.ws = await self._connect_with_headers(current_url, headers)
            self.logger.info("Connected to WebSocket server")
            return True
        except Exception as e:
            if "HTTP 401" in str(e) or "401" in str(e):
                self.logger.error("WebSocket authentication failed - invalid or missing tokens")
                self.logger.error("Please check that your tokens are valid and not expired")
                self.logger.error(f"Error details: {e}")
                self.logger.error(f"Current tokens: {tokens}")
            else:
                self.logger.error(f"Failed to connect to WebSocket: {e}")
                # Try alternative URL if the primary one fails
                if mode == WebSocketMode.NEW_PAIRS and "cluster-usc2" in self.ws_url:
                    try:
                        alternative_url = Websockets.CLUSTER_3
                        self.logger.info(f"Trying alternative WebSocket URL: {alternative_url}")
                        self.ws = await self._connect_with_headers(alternative_url, headers)
                        self.logger.info("Connected to alternative WebSocket server")
                        return True
                    except Exception as e2:
                        self.logger.error(f"Alternative WebSocket connection also failed: {e2}")
            return False
            
    async def _message_handler(self):
        """Expected to be implemented by MessageHandlerMixin"""
        raise NotImplementedError

    async def ensure_connection_and_listen(self):
        """Ensure WebSocket connection is established and start listening for messages."""
        if not self.ws:
            if not await self.connect(mode=WebSocketMode.NEW_PAIRS):
                return
        
        # We need to call the handler. Since it lives on 'self' via mixin:
        await self._message_handler()

    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.logger.info("WebSocket connection closed")
