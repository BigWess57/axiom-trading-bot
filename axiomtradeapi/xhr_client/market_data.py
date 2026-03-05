from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from ..auth.auth_manager import AuthManager
    from ..content.endpoints import Endpoints

class MarketDataMixin:
    """Market data related methods for AxiomTradeClient"""
    
    # Type hinting for mixin dependencies
    auth_manager: 'AuthManager'
    endpoints: 'Endpoints'
    
    def ensure_authenticated(self) -> bool:
        """Helper to ensure authentication (implemented in AuthMixin)"""
        raise NotImplementedError
        
    def get_trending_tokens(self, time_period: str = '1h') -> Dict:
        """
        Get trending meme tokens
        Available time periods: 1h, 24h, 7d
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.TRENDING_MEME}?timePeriod={time_period}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get trending tokens: {e}")
    
    # DOES NOT WORK
    def get_token_info(self, token_address: str) -> Dict:
        """
        Get information about a specific token
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        # This endpoint might need to be confirmed with actual API documentation
        url = f'{self.endpoints.TOKEN_DETAILS}/{token_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get token info: {e}")
            
    def get_token_info_by_pair(self, pair_address: str) -> Dict:
        """
        Get token information by pair address
        
        Args:
            pair_address (str): The pair address to get info for
            
        Returns:
            Dict: Token information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.TOKEN_INFO}?pairAddress={pair_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get token info: {e}")
    
    def get_last_transaction(self, pair_address: str) -> Dict:
        """
        Get last transaction for a pair
        
        Args:
            pair_address (str): The pair address to get last transaction for
            
        Returns:
            Dict: Last transaction information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.LAST_TRANSACTION}?pairAddress={pair_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get last transaction: {e}")
    
    def get_pair_info(self, pair_address: str) -> Dict:
        """
        Get pair information
        
        Args:
            pair_address (str): The pair address to get info for
            
        Returns:
            Dict: Pair information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.PAIR_INFO}?pairAddress={pair_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get pair info: {e}")
    
    def get_pair_stats(self, pair_address: str) -> Dict:
        """
        Get pair statistics
        
        Args:
            pair_address (str): The pair address to get stats for
            
        Returns:
            Dict: Pair statistics
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.PAIR_STATS}?pairAddress={pair_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get pair stats: {e}")
    
    def get_meme_open_positions(self, wallet_address: str) -> Dict:
        """
        Get open meme token positions for a wallet
        
        Args:
            wallet_address (str): The wallet address to get positions for
            
        Returns:
            Dict: Open positions information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.MEME_OPEN_POSITIONS}?walletAddress={wallet_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get open positions: {e}")
    
    def get_holder_data(self, pair_address: str, only_tracked_wallets: bool = False) -> Dict:
        """
        Get holder data for a pair
        
        Args:
            pair_address (str): The pair address to get holder data for
            only_tracked_wallets (bool): Whether to only include tracked wallets
            
        Returns:
            Dict: Holder data information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.HOLDER_DATA}?pairAddress={pair_address}&onlyTrackedWallets={str(only_tracked_wallets).lower()}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get holder data: {e}")
    
    def get_dev_tokens(self, dev_address: str) -> Dict:
        """
        Get tokens created by a developer address
        
        Args:
            dev_address (str): The developer address to get tokens for
            
        Returns:
            Dict: Developer tokens information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.DEV_TOKENS}?devAddress={dev_address}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get dev tokens: {e}")
    
    def get_token_analysis(self, dev_address: str, token_ticker: str) -> Dict:
        """
        Get token analysis for a developer and token ticker
        
        Args:
            dev_address (str): The developer address
            token_ticker (str): The token ticker to analyze
            
        Returns:
            Dict: Token analysis information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.TOKEN_ANALYSIS}?devAddress={dev_address}&tokenTicker={token_ticker}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get token analysis: {e}")

    def get_market_weather(self) -> Dict:
        """
        Get market weather information
        
        Returns:
            Dict: Market weather information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = f'{self.endpoints.MARKET_LIGHTHOUSE}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get market weather: {e}")

    def get_pair_chart(self,
                    pair_address: str,
                    from_ts: int,
                    to_ts: int,
                    open_trading: int,
                    pair_created_at: int,
                    last_transaction_time: int,
                    currency: str = "USD",
                    interval: str = "1s",
                    count_bars: int = 300,
                    show_outliers: bool = False,
                    is_new: bool = False,
                    v: int = None) -> Dict:
        """
        Get chart data (candles) for a pair.
        
        Args:
            pair_address (str): Pair address
            from_ts (int): Start timestamp (ms)
            to_ts (int): End timestamp (ms)
            open_trading (int): Open trading timestamp (ms)
            pair_created_at (int): Pair created at timestamp (ms)
            last_transaction_time (int): Last transaction timestamp (ms)
            currency (str): Currency (default "USD")
            interval (str): Interval (default "1s")
            count_bars (int): Number of bars
            show_outliers (bool): Show outliers
            is_new (bool): Is new pair
            v (int, optional): Version/timestamp (ms), defaults to to_ts if None
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        if v is None:
            v = to_ts
            
        params = {
            "pairAddress": pair_address,
            "from": from_ts,
            "to": to_ts,
            "currency": currency,
            "interval": interval,
            "openTrading": open_trading,
            "pairCreatedAt": pair_created_at,
            "lastTransactionTime": last_transaction_time,
            "countBars": count_bars,
            "showOutliers": str(show_outliers).lower(),
            "isNew": str(is_new).lower(),
            "v": v
        }
        
        # Construct query string manually to ensure consistency or use requests params
        # Using f-string for consistency with other methods in this file
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f'{self.endpoints.PAIR_CHART}?{query_string}'
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get pair chart: {e}")
