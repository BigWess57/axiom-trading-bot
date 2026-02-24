import logging
import inspect
import websockets
from typing import Optional, Dict, Callable

from ..content.endpoints import BaseUrls, Websockets

from .types import WebSocketMode
from .connection import ConnectionMixin
from .subscription import SubscriptionMixin
from .handler import MessageHandlerMixin

class AxiomTradeWebSocketClient(MessageHandlerMixin, ConnectionMixin, SubscriptionMixin):    
    def __init__(self, auth_manager, log_level=logging.INFO) -> None:
        self.ws_url = Websockets.MAIN
        self.ws_url_token_price = Websockets.TOKEN_PRICE
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
        if not auth_manager:
            raise ValueError("auth_manager is required and must be an authenticated AuthManager instance")
        
        self.auth_manager = auth_manager
        
        # Setup logging
        self.logger = logging.getLogger("AxiomTradeWebSocket")
        self.logger.setLevel(log_level)
        
        # Create console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(log_level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self._callbacks: Dict[str, Callable] = {}
        
        # Pulse-specific tracking
        self._pulse_message_count = 0
        
        # Detect which parameter name to use for headers based on websockets.connect signature
        sig = inspect.signature(websockets.connect)
        self._uses_additional_headers = 'additional_headers' in sig.parameters
        self._uses_extra_headers = 'extra_headers' in sig.parameters
        
        if self._uses_additional_headers:
            self.logger.debug("Using 'additional_headers' parameter for websockets (version 13+)")
        elif self._uses_extra_headers:
            self.logger.debug("Using 'extra_headers' parameter for websockets (version 10.x)")
        else:
            self.logger.warning("Could not detect headers parameter name for websockets.connect")

# Re-export WebSocketMode for convenience
__all__ = ['AxiomTradeWebSocketClient', 'WebSocketMode']
