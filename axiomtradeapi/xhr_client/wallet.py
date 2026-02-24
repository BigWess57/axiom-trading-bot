from typing import List, Optional, Dict, Union, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..auth.auth_manager import AuthManager
    from ..content.endpoints import Endpoints

class WalletMixin:
    """Wallet and balance related methods for AxiomTradeClient"""
    
    # Type hinting for mixin dependencies
    auth_manager: 'AuthManager'
    endpoints: 'Endpoints'
    logger: logging.Logger
    
    def ensure_authenticated(self) -> bool:
        """Helper to ensure authentication (implemented in AuthMixin)"""
        raise NotImplementedError
        
    # DOES NOT WORK
    def get_user_portfolio(self) -> Dict:
        """
        Get user's portfolio information
        """
        # Ensure we have valid authentication
        if not self.ensure_authenticated():
            raise ValueError("Authentication failed. Please login first.")
        
        url = self.endpoints.PORTFOLIO
        
        try:
            response = self.auth_manager.make_authenticated_request('GET', url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get portfolio: {e}")
            
    def get_token_balance(self, wallet_address: str, token_mint: str) -> Optional[float]:
        """
        Get the balance of a specific token for a wallet.
        
        Args:
            wallet_address (str): Wallet public key
            token_mint (str): Token mint address
            
        Returns:
            Token balance as float, or None if error
        """
        try:
            # Ensure we have valid authentication
            if not self.ensure_authenticated():
                raise ValueError("Authentication failed")
            
            payload = {
                "publicKey": wallet_address,
                "tokenMint": token_mint
            }
            
            url = f"{self.endpoints.BASE_URL_API}{self.endpoints.ENDPOINT_GET_TOKEN_BALANCE}"
            response = self.auth_manager.make_authenticated_request('POST', url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                balance = result.get("balance", 0)
                self.logger.info(f"Token balance for {token_mint}: {balance}")
                return float(balance)
            else:
                self.logger.error(f"Failed to get token balance: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting token balance: {str(e)}")
            return None
    
    def get_batched_sol_balance(self, wallet_addresses: List[str]) -> Dict[str, float]:
        """
        Get SOL balance for multiple wallet addresses using the batched endpoint.

        Args:
            wallet_addresses (List[str]): List of wallet public keys

        Returns:
            Dict[str, float]: Dictionary mapping wallet addresses to their SOL balance
        """
        try:
            # Ensure we have valid authentication
            if not self.ensure_authenticated():
                raise ValueError("Authentication failed")

            # Check if we have the batched endpoint defined
            if not hasattr(self.endpoints, 'ENDPOINT_GET_BATCHED_BALANCE'):
                 # Fallback if somehow using an older endpoints file, though we checked it exists
                 url = f"{self.endpoints.BASE_URL_API}/batched-sol-balance"
            else:
                 url = self.endpoints.ENDPOINT_GET_BATCHED_BALANCE

            payload = {
                "publicKeys": wallet_addresses
            }

            self.logger.info(f"Fetching batched SOL balance for {len(wallet_addresses)} using {url}")
            response = self.auth_manager.make_authenticated_request('POST', url, json=payload)
            print(response.text)
            if response.status_code == 200:
                data = response.json()
                results = {}
                
                # Handle list response (based on user's test script finding)
                if isinstance(data, list):
                    # If we can't easily map, let's just return the raw data or try to map by index if count matches
                    if len(data) == len(wallet_addresses):
                         for i, item in enumerate(data):
                             if isinstance(item, dict):
                                 val = item.get('sol') or item.get('solBalance') or item.get('balance')
                                 if val is not None:
                                     results[wallet_addresses[i]] = float(val)
                
                elif isinstance(data, dict):
                     # If it's a dict, it might be {address: {sol: ..., ...}} or {address: balance}
                     for addr, val in data.items():
                         if isinstance(val, dict):
                             # Key could be 'sol', 'solBalance', 'balance'
                             sol_val = val.get('sol') or val.get('solBalance') or val.get('balance')
                             
                             if sol_val is not None:
                                 results[addr] = float(sol_val)
                         elif isinstance(val, (int, float, str)):
                             try:
                                 results[addr] = float(val)
                             except:
                                 pass
                
                return results
            else:
                self.logger.error(f"Failed to get batched SOL balance: {response.status_code} - {response.text}")
                return {}

        except Exception as e:
            self.logger.error(f"Error getting batched SOL balance: {str(e)}")
            return {}

    def get_sol_balance(self, wallet_address: str) -> Optional[float]:
        """
        Get SOL balance for a wallet address using batched endpoint.
        
        Args:
            wallet_address (str): Wallet public key
            
        Returns:
            SOL balance as float, or None if error
        """
        try:
            # Internal call to batched version
            results = self.get_batched_sol_balance([wallet_address])
            return results.get(wallet_address)
                
        except Exception as e:
            self.logger.error(f"Error getting SOL balance: {str(e)}")
            return None
    
    # Backward compatibility aliases for old _client.py API
    def GetBalance(self, wallet_address: str) -> Dict[str, Union[float, int]]:
        """
        Legacy method for backward compatibility. 
        Use get_sol_balance() for new code.
        """
        balance_sol = self.get_sol_balance(wallet_address)
        if balance_sol is not None:
            lamports = int(balance_sol * 1_000_000_000)
            return {
                "sol": balance_sol,
                "lamports": lamports,
                "slot": 0  # Not available from this method
            }
        return None
