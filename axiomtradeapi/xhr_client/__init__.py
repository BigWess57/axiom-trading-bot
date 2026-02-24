from __future__ import annotations
import logging
from typing import Dict, Optional

from ..auth.auth_manager import AuthManager
from ..content.endpoints import Endpoints
from ..websocket.client import AxiomTradeWebSocketClient

from .auth import AuthMixin
from .market_data import MarketDataMixin
from .trading import TradingMixin
from .wallet import WalletMixin

class AxiomTradeClient(AuthMixin, MarketDataMixin, TradingMixin, WalletMixin):
    """
    Main client for interacting with Axiom Trade API with automatic token management.
    Now refactored to use mixins for better organization.
    """
    
    def __init__(self, username: str = None, password: str = None, 
                 auth_token: str = None, refresh_token: str = None,
                 storage_dir: str = None, use_saved_tokens: bool = True):
        """
        Initialize AxiomTradeClient with enhanced authentication
        
        Args:
            username: Email for automatic login
            password: Password for automatic login  
            auth_token: Existing auth token (optional)
            refresh_token: Existing refresh token (optional)
            storage_dir: Directory for secure token storage
            use_saved_tokens: Whether to load/save tokens automatically (default: True)
        """
        # Initialize the enhanced auth manager
        self.auth_manager = AuthManager(
            username=username,
            password=password,
            auth_token=auth_token,
            refresh_token=refresh_token,
            storage_dir=storage_dir,
            use_saved_tokens=use_saved_tokens
        )
        
        # Initialize endpoints for trading functionality
        self.endpoints = Endpoints()
        
        # Keep backward compatibility
        self.auth = self.auth_manager  # For legacy code
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': self.endpoints.BASE_URL,
            'Connection': 'keep-alive',
            'Referer': f'{self.endpoints.BASE_URL}/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site'
        }
    
    def get_websocket_client(self, log_level=logging.INFO) -> AxiomTradeWebSocketClient:
        """
        Get an instance of the WebSocket client using current authentication.
        
        Args:
            log_level: Logging level for the WebSocket client
            
        Returns:
            AxiomTradeWebSocketClient: Initialized WebSocket client
        """
        return AxiomTradeWebSocketClient(self.auth_manager, log_level=log_level)


# Convenience functions for quick usage
def quick_login_and_get_trending(email: str, b64_password: str, otp_code: str, time_period: str = '1h') -> Dict:
    """
    Quick function to login and get trending tokens in one call
    """
    client = AxiomTradeClient()
    # Correction: I'll just pass email and password.
    client.login(email, b64_password) 
    return client.get_trending_tokens(time_period)
    # client = AxiomTradeClient()
    # client.login(email, b64_password, otp_code)
    # return client.get_trending_tokens(time_period)

def get_trending_with_token(access_token: str, time_period: str = '1h') -> Dict:
    """
    Quick function to get trending tokens with existing access token
    """
    client = AxiomTradeClient()
    client.set_tokens(access_token=access_token, refresh_token="") # refresh_token is required in set_tokens signature: def set_tokens(self, access_token: str, refresh_token: str)
    
    client.set_tokens(access_token, "")
    return client.get_trending_tokens(time_period)
    # client = AxiomTradeClient()
    # client.set_tokens(access_token=access_token)
    # return client.get_trending_tokens(time_period)
