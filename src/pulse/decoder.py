"""
Pulse Decoder Module

This module handles the decoding of Pulse WebSocket messages.
It parses MessagePack data and converts it into structured Python objects.
"""
from typing import Dict, Any, List, Optional
import logging
import msgpack

from src.pulse.types import PulseToken

logger = logging.getLogger(__name__)

class PulseDecoder:
    """Decodes Pulse WebSocket messages"""
    
    def decode_message(self, message: bytes) -> Dict[str, Any]:
        """Decode a MessagePack message from bytes"""
        try:
            unpacked = msgpack.unpackb(message, raw=False)
            return unpacked
        except Exception as e:
            logger.error(f"Failed to decode MessagePack: {e}")
            return None

    def parse_snapshot(self, data: List[Any]) -> Dict[str, List[PulseToken]]:
        """Parse Type 0 (Snapshot) message"""
        # [0, {"newPairs": [...], "finalStretch": [...], "migrated": [...]}]
        if not data or len(data) < 2 or data[0] != 0:
            return {}
            
        categories = data[1]
        result = {
            "newPairs": [],
            "finalStretch": [],
            "migrated": []
        }
        
        # New Pairs
        if "newPairs" in categories:
            result["newPairs"] = [PulseToken.from_array(t) for t in categories["newPairs"]]
            
        # Final Stretch
        if "finalStretch" in categories:
            result["finalStretch"] = [PulseToken.from_array(t) for t in categories["finalStretch"]]
            
        # Migrated
        if "migrated" in categories:
            result["migrated"] = [PulseToken.from_array(t) for t in categories["migrated"]]
            
        return result

    def parse_new_token(self, data: List[Any]) -> Optional[tuple[str, PulseToken]]:
        """Parse Type 2 (New Token) message
        
        Type 2 messages provide full token data when a token starts being monitored.
        Structure: [2, [category, token_data_array]]
        
        Args:
            data: The Type 2 message data
            
        Returns:
            Tuple of (category, PulseToken) if successful, None otherwise
            category is one of: "newPairs", "finalStretch", "migrated"
        """
        # Validate Type 2 structure: [2, [category, token_data_array]]
        if not data or len(data) < 2 or data[0] != 2:
            return None
            
        if not isinstance(data[1], list) or len(data[1]) < 2:
            logger.warning(f"Invalid Type 2 structure: {data}")
            return None
            
        category = data[1][0]  # "newPairs", "finalStretch", or "migrated"
        token_data_array = data[1][1]  # Full token data (same format as snapshot)
        
        if not isinstance(token_data_array, list):
            logger.warning(f"Invalid token data in Type 2: {token_data_array}")
            return None
        
        try:
            # Parse the token data using the same method as snapshots
            token = PulseToken.from_array(token_data_array)
            # logger.info(f"New token detected: {token.name} ({token.ticker}) in {category}")
            return (category, token)
        except Exception as e:
            logger.error(f"Failed to parse Type 2 token data: {e}")
            return None

    def parse_remove(self, data: List[Any]) -> Optional[tuple[str, str]]:
        """Parse Type 3 (Remove Token) message
        
        Type 3 messages indicate a token should be removed from monitoring.
        Structure: [3, [category, token_address]]
        
        Args:
            data: The Type 3 message data
            
        Returns:
            Tuple of (category, pair_address) if successful, None otherwise
            category is one of: "newPairs", "finalStretch", "migrated"
        """
        # Validate Type 3 structure: [3, [category, token_address]]
        if not data or len(data) < 2 or data[0] != 3:
            return None
            
        if not isinstance(data[1], list) or len(data[1]) < 2:
            logger.warning(f"Invalid Type 3 structure: {data}")
            return None
            
        category = data[1][0]  # "newPairs", "finalStretch", or "migrated"
        pair_address = data[1][1]  # Token pair address to remove
        
        if not isinstance(pair_address, str):
            logger.warning(f"Invalid token address in Type 3: {pair_address}")
            return None
        
        # logger.info(f"Token removal: {pair_address[:20]}... from {category}")
        return (category, pair_address)

    def parse_update(self, data: List[Any], current_tokens: Dict[str, PulseToken]) -> Optional[PulseToken]:
        """Parse Type 1 (Update) message"""
        # [1, "pair_address", [[field_id, value], ...]]
        if not data or len(data) < 3 or data[0] != 1:
            return None
            
        pair_address = data[1]
        updates = data[2]
        
        if pair_address not in current_tokens:
            return None
            
        token = current_tokens[pair_address]
        
        # Apply updates
        for field_id, value in updates:
            # Update raw_fields mapping for debugging
            token.raw_fields[field_id] = value
            
            try:
                # Holder Analysis
                if field_id == 13:
                    token.top10_holders_percent = float(value)
                elif field_id == 14:
                    token.dev_holding_percent = float(value)
                elif field_id == 15:
                    token.snipers_percent = float(value)
                elif field_id == 16:
                    token.insiders_percent = float(value)
                elif field_id == 17:
                    token.bundled_percent = float(value)
                elif field_id == 28:
                    token.holders = int(value)
                
                # Financial Metrics
                elif field_id == 18:
                    token.volume_total = float(value)
                elif field_id == 19:
                    token.market_cap = float(value)
                elif field_id == 20:
                    token.fees_paid = float(value)
                elif field_id == 26:
                    token.bonding_curve_percentage = float(value)
                elif field_id == 27:
                    token.total_supply = float(value)
                
                # Activity
                elif field_id == 23:
                    token.txns_total = int(value)
                elif field_id == 24:
                    token.buys_total = int(value)
                elif field_id == 25:
                    token.sells_total = int(value)
                elif field_id == 29:
                    token.pro_traders_count = int(value)
                
                # Dev Info
                elif field_id == 33:
                    token.dev_tokens_migrated = int(value)
                elif field_id == 41:
                    token.dev_tokens_created = int(value)
                
                # Social Metrics
                elif field_id == 40:
                    token.famous_kols = int(value)
                elif field_id == 45:
                    token.active_users_watching = int(value)
                elif field_id == 47:
                    token.twitter_followers = int(value)
                    
            except (ValueError, TypeError):
                logger.debug(f"Failed to parse field {field_id} with value {value}")
                continue
                
        return token
                

##### UNUSED FOR NOW #####
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PulseToken':
        """Create from JSON dict (new_pairs event)"""
        # Map JSON keys to PulseToken fields based on standard Axiom API response
        return cls(
            pair_address=data.get("pairAddress", "") or "",
            token_mint=data.get("baseToken", {}).get("address", "") or "",
            name=data.get("baseToken", {}).get("name", "") or "Unknown",
            ticker=data.get("baseToken", {}).get("symbol", "") or "UNK",
            image=data.get("info", {}).get("imageUrl", "") or "",
            market_cap=float(data.get("marketCap", 0) or 0),
            liquidity=float(data.get("liquidity", {}).get("usd", 0) or 0),
            volume_5m=float(data.get("volume", {}).get("h1", 0) or 0),
            holders=0, # JSON usually missing detailed holders
            created_at=str(data.get("pairCreatedAt", "")),
            
            # Defaults for fields not in JSON summary
            txns_5m=0,
            buys_5m=0,
            sells_5m=0,
            active_users=0,
            kols_count=0,
            pro_traders_count=0,
            dev_holding_percent=0.0,
            insiders_percent=0.0,
            
            raw_data=[] 
        )
