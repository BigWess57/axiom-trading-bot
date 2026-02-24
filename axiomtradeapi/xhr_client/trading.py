from typing import Dict, Union, TYPE_CHECKING
import requests
import base64
import logging

if TYPE_CHECKING:
    from ..auth.auth_manager import AuthManager
    from ..content.endpoints import Endpoints
    from solders.keypair import Keypair
    from solders.transaction import Transaction
    from solders.pubkey import Pubkey

# Trading-related imports availability checks
try:
    from solders.keypair import Keypair
    from solders.transaction import Transaction
    from solders.pubkey import Pubkey
    SOLDERS_AVAILABLE = True
except ImportError:
    SOLDERS_AVAILABLE = False
    Keypair = None
    Transaction = None
    Pubkey = None

try:
    import base58
    BASE58_AVAILABLE = True
except ImportError:
    BASE58_AVAILABLE = False

class TradingMixin:
    """Trading related methods for AxiomTradeClient"""
    
    # Type hinting for mixin dependencies
    auth_manager: 'AuthManager'
    endpoints: 'Endpoints'
    logger: logging.Logger
    
    def send_transaction_to_rpc(self, signed_transaction_base64: str, 
                               rpc_url: str = "https://greer-651y13-fast-mainnet.helius-rpc.com/") -> Dict[str, Union[str, bool]]:
        """
        Send a base64 encoded signed transaction directly to Solana RPC endpoint.
        (Legacy method for backward compatibility)
        
        Args:
            signed_transaction_base64 (str): Base64 encoded signed transaction
            rpc_url (str): Solana RPC endpoint URL
            
        Returns:
            Dict with transaction signature and success status
        """
        try:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9,es;q=0.8,fr;q=0.7,de;q=0.6,ru;q=0.5',
                'content-type': 'application/json',
                'origin': self.endpoints.BASE_URL,
                'priority': 'u=1, i',
                'referer': f'{self.endpoints.BASE_URL}/',
                'sec-ch-ua': '"Opera GX";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0'
            }
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    signed_transaction_base64,
                    {
                        "encoding": "base64",
                        "skipPreflight": True,
                        "preflightCommitment": "confirmed",
                        "maxRetries": 0
                    }
                ]
            }
            
            self.logger.info(f"Sending base64 transaction to RPC: {rpc_url}")
            
            response = requests.post(rpc_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    signature = result["result"]
                    self.logger.info(f"Transaction sent successfully. Signature: {signature}")
                    return {
                        "success": True,
                        "signature": signature,
                        "transactionId": signature,
                        "explorer_url": f"https://solscan.io/tx/{signature}"
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Unexpected RPC response: {result}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"Failed to send transaction: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error sending transaction to RPC: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    # ==================== TRADING METHODS ====================
    
    def buy_token(self, private_key: str, token_mint: str, amount: float, 
                  slippage_percent: float = 10, priority_fee: float = 0.005, 
                  pool: str = "auto", denominated_in_sol: bool = True,
                  rpc_url: str = "https://api.mainnet-beta.solana.com/") -> Dict[str, Union[str, bool]]:
        """
        Buy a token using SOL via PumpPortal API following their exact specification.
        
        Args:
            private_key (str): Private key as base58 string
            token_mint (str): Token mint address to buy
            amount (float): Amount of SOL or tokens to trade
            slippage_percent (float): Slippage tolerance percentage (default: 10%)
            priority_fee (float): Priority fee in SOL (default: 0.005)
            pool (str): Exchange to trade on - "pump", "raydium", "pump-amm", 
                       "launchlab", "raydium-cpmm", "bonk", or "auto" (default: "auto")
            denominated_in_sol (bool): True if amount is SOL, False if amount is tokens (default: True)
            rpc_url (str): Solana RPC endpoint URL
            
        Returns:
            Dict with transaction signature and success status
        """
        if not SOLDERS_AVAILABLE:
            return {
                "success": False, 
                "error": "solders library not installed. Run: pip install solders"
            }
        
        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
            from solders.commitment_config import CommitmentLevel
            from solders.rpc.requests import SendVersionedTransaction
            from solders.rpc.config import RpcSendTransactionConfig
            
            # Convert private key to Keypair - use Keypair.from_base58_string as per PumpPortal example
            keypair = Keypair.from_base58_string(private_key)
            public_key = str(keypair.pubkey())
            
            self.logger.info(
                "\n"
                "================= BUY ORDER =================\n"
                f"  Action:            BUY\n"
                f"  Token Mint:        {token_mint}\n"
                f"  Amount:            {amount} {'SOL' if denominated_in_sol else 'tokens'}\n"
                f"  Slippage:          {int(slippage_percent)}%\n"
                f"  Priority Fee:      {priority_fee} SOL\n"
                f"  Pool:              {pool}\n"
                f"  Buyer Public Key:  {public_key}\n"
                "============================================="
            )
            
            # Prepare trade data exactly as PumpPortal expects
            # According to PumpPortal docs (https://pumpportal.fun/local-trading-api/trading-api): amount should be in SOL or tokens.
            trade_data = {
                "publicKey": public_key,
                "action": "buy",
                "mint": token_mint,
                "amount": amount,
                "denominatedInSol": "true" if denominated_in_sol else "false",
                "slippage": int(slippage_percent),
                "priorityFee": priority_fee,
                "pool": pool
            }
            
            self.logger.info(f"Sending trade request to PumpPortal with data: {trade_data}")
            
            # Get transaction from PumpPortal exactly as shown in their example
            response = requests.post(url=self.endpoints.TRADE_LOCAL, data=trade_data)
            
            if response.status_code != 200:
                error_msg = f"PumpPortal API error: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Create transaction exactly as PumpPortal shows
            tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [keypair])
            
            # Configure and send transaction exactly as PumpPortal example
            commitment = CommitmentLevel.Confirmed
            config = RpcSendTransactionConfig(preflight_commitment=commitment)
            txPayload = SendVersionedTransaction(tx, config)
            
            # Send to RPC endpoint exactly as PumpPortal example
            response = requests.post(
                url=rpc_url,
                headers={"Content-Type": "application/json"},
                data=txPayload.to_json()
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tx_signature = result['result']
                    self.logger.info(f"Transaction successful. Signature: {tx_signature}")
                    return {
                        "success": True,
                        "signature": tx_signature,
                        "transactionId": tx_signature,
                        "explorer_url": f"https://solscan.io/tx/{tx_signature}"
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Unexpected RPC response: {result}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"Failed to send transaction: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Error in buy_token: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def sell_token(self, private_key: str, token_mint: str, amount: Union[float, str], 
                   slippage_percent: float = 10, priority_fee: float = 0.005, 
                   pool: str = "auto", denominated_in_sol: bool = False,
                   rpc_url: str = "https://api.mainnet-beta.solana.com/") -> Dict[str, Union[str, bool]]:
        """
        Sell a token for SOL via PumpPortal API following their exact specification.
        
        Args:
            private_key (str): Private key as base58 string
            token_mint (str): Token mint address to sell
            amount (Union[float, str]): Amount of tokens or SOL to trade. Can be:
                                      - float: Exact number of tokens/SOL
                                      - str: Percentage like "100%" to sell all owned tokens
            slippage_percent (float): Slippage tolerance percentage (default: 10%)
            priority_fee (float): Priority fee in SOL (default: 0.005)
            pool (str): Exchange to trade on - "pump", "raydium", "pump-amm", 
                       "launchlab", "raydium-cpmm", "bonk", or "auto" (default: "auto")
            denominated_in_sol (bool): True if amount is SOL, False if amount is tokens (default: False)
            rpc_url (str): Solana RPC endpoint URL
            
        Returns:
            Dict with transaction signature and success status
        """
        if not SOLDERS_AVAILABLE:
            return {
                "success": False, 
                "error": "solders library not installed. Run: pip install solders"
            }
        
        try:
            from solders.keypair import Keypair
            from solders.transaction import VersionedTransaction
            from solders.commitment_config import CommitmentLevel
            from solders.rpc.requests import SendVersionedTransaction
            from solders.rpc.config import RpcSendTransactionConfig
            
            # Convert private key to Keypair - use Keypair.from_base58_string as per PumpPortal example
            keypair = Keypair.from_base58_string(private_key)
            public_key = str(keypair.pubkey())
            
            # Handle amount parameter - can be float or percentage string like "100%"
            amount_str_or_float = str(amount) if isinstance(amount, str) else amount
            
            self.logger.info(
                "\n"
                "================= SELL ORDER =================\n"
                f"  Action:            SELL\n"
                f"  Token Mint:        {token_mint}\n"
                f"  Amount:            {amount_str_or_float} {'SOL' if denominated_in_sol else 'tokens'}\n"
                f"  Slippage:          {int(slippage_percent)}%\n"
                f"  Priority Fee:      {priority_fee} SOL\n"
                f"  Pool:              {pool}\n"
                f"  Seller Public Key: {public_key}\n"
                "============================================="
            )
            
            # Prepare trade data exactly as PumpPortal expects
            # According to PumpPortal docs: amount can be number or percentage string like "100%"
            trade_data = {
                "publicKey": public_key,
                "action": "sell",
                "mint": token_mint,
                "amount": amount_str_or_float,  # Send amount as-is - can be number or percentage string
                "denominatedInSol": "true" if denominated_in_sol else "false",
                "slippage": int(slippage_percent),
                "priorityFee": priority_fee,
                "pool": pool
            }
            
            self.logger.info(f"Sending trade request to PumpPortal with data: {trade_data}")
            
            # Get transaction from PumpPortal exactly as shown in their example
            response = requests.post(url=self.endpoints.TRADE_LOCAL, data=trade_data)
            
            if response.status_code != 200:
                error_msg = f"PumpPortal API error: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Create transaction exactly as PumpPortal shows
            tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [keypair])
            
            # Configure and send transaction exactly as PumpPortal example
            commitment = CommitmentLevel.Confirmed
            config = RpcSendTransactionConfig(preflight_commitment=commitment)
            txPayload = SendVersionedTransaction(tx, config)
            
            # Send to RPC endpoint exactly as PumpPortal example
            response = requests.post(
                url=rpc_url,
                headers={"Content-Type": "application/json"},
                data=txPayload.to_json()
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tx_signature = result['result']
                    self.logger.info(f"Transaction successful. Signature: {tx_signature}")
                    return {
                        "success": True,
                        "signature": tx_signature,
                        "transactionId": tx_signature,
                        "explorer_url": f"https://solscan.io/tx/{tx_signature}"
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Unexpected RPC response: {result}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"Failed to send transaction: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Error in sell_token: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _send_transaction_to_rpc(self, signed_transaction, 
                                rpc_url: str = "https://greer-651y13-fast-mainnet.helius-rpc.com/") -> Dict[str, Union[str, bool]]:
        """
        Send a signed VersionedTransaction to Solana RPC endpoint.
        
        Args:
            signed_transaction: VersionedTransaction object that's already signed
            rpc_url (str): Solana RPC endpoint URL
            
        Returns:
            Dict with transaction signature and success status
        """
        try:
            from solders.commitment_config import CommitmentLevel
            from solders.rpc.requests import SendVersionedTransaction
            from solders.rpc.config import RpcSendTransactionConfig
            
            # Configure transaction sending
            commitment = CommitmentLevel.Confirmed
            config = RpcSendTransactionConfig(preflight_commitment=commitment)
            tx_payload = SendVersionedTransaction(signed_transaction, config)
            
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9,es;q=0.8,fr;q=0.7,de;q=0.6,ru;q=0.5',
                'content-type': 'application/json',
                'origin': 'https://axiom.trade',
                'priority': 'u=1, i',
                'referer': 'https://axiom.trade/',
                'sec-ch-ua': '"Opera GX";v="120", "Not-A.Brand";v="8", "Chromium";v="135"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 OPR/120.0.0.0'
            }
            
            self.logger.info(f"Sending transaction to RPC: {rpc_url}")
            
            response = requests.post(
                url=rpc_url,
                headers=headers,
                data=tx_payload.to_json(),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    signature = result["result"]
                    self.logger.info(f"Transaction sent successfully. Signature: {signature}")
                    return {
                        "success": True,
                        "signature": signature,
                        "transactionId": signature,
                        "explorer_url": f"https://solscan.io/tx/{signature}"
                    }
                elif "error" in result:
                    error_msg = f"RPC Error: {result['error']}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
                else:
                    error_msg = f"Unexpected RPC response: {result}"
                    self.logger.error(error_msg)
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"Failed to send transaction: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error sending transaction to RPC: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _get_keypair_from_private_key(self, private_key: str) -> 'Keypair':
        """Convert private key string to Keypair object."""
        if not SOLDERS_AVAILABLE:
            raise ImportError("solders library not installed. Run: pip install solders")
        
        try:
            if isinstance(private_key, str):
                # Try to decode as base58 first
                try:
                    if BASE58_AVAILABLE:
                        import base58
                        private_key_bytes = base58.b58decode(private_key)
                    else:
                        # Fallback to assuming it's hex
                        private_key_bytes = bytes.fromhex(private_key)
                except:
                    # Try as hex string
                    try:
                        private_key_bytes = bytes.fromhex(private_key)
                    except:
                        # Try as base64
                        try:
                            private_key_bytes = base64.b64decode(private_key)
                        except:
                            raise ValueError("Unable to decode private key")
            else:
                private_key_bytes = private_key
            
            return Keypair.from_bytes(private_key_bytes)
        except Exception as e:
            raise ValueError(f"Invalid private key format: {e}")
    
    def _sign_and_send_transaction(self, keypair: 'Keypair', transaction_data: Dict) -> Dict[str, Union[str, bool]]:
        """Sign and send a transaction to the Solana network."""
        if not SOLDERS_AVAILABLE:
            return {
                "success": False, 
                "error": "solders library not installed. Run: pip install solders"
            }
        
        try:
            # Extract transaction from response
            if "transaction" in transaction_data:
                transaction_b64 = transaction_data["transaction"]
            elif "serializedTransaction" in transaction_data:
                transaction_b64 = transaction_data["serializedTransaction"]
            else:
                raise ValueError("No transaction found in API response")
            
            # Decode and deserialize transaction
            transaction_bytes = base64.b64decode(transaction_b64)
            transaction = Transaction.from_bytes(transaction_bytes)
            
            # Sign the transaction
            signed_transaction = transaction
            signed_transaction.sign([keypair])
            
            # Send the signed transaction back to API
            send_data = {
                "signedTransaction": base64.b64encode(bytes(signed_transaction)).decode('utf-8')
            }
            
            url = f"{self.endpoints.BASE_URL_API}{self.endpoints.ENDPOINT_SEND_TRANSACTION}"
            response = self.auth_manager.make_authenticated_request('POST', url, json=send_data)
            
            if response.status_code == 200:
                result = response.json()
                signature = result.get("signature", "")
                self.logger.info(f"Transaction sent successfully. Signature: {signature}")
                return {
                    "success": True,
                    "signature": signature,
                    "transactionId": signature
                }
            else:
                error_msg = f"Failed to send transaction: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"Error signing/sending transaction: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
