from typing import Dict, List, Optional, Any, Callable
import logging
from .decoder import PulseDecoder, PulseToken

logger = logging.getLogger(__name__)

class PulseTracker:
    """
    Manages the state of tracked tokens from the Pulse WebSocket feed.
    
    Message Types:
    - Type 0 (Snapshot): Initial full state of all monitored tokens
    - Type 1 (Update): Incremental field updates for existing tokens
    - Type 2 (New Token): Full data for newly monitored token
    - Type 3 (Remove Token): Explicit removal of token from monitoring
    """
    def __init__(self):
        self.decoder = PulseDecoder()
        # Storage: pair_address -> PulseToken
        self.tokens: Dict[str, PulseToken] = {}
        # Storage: category -> Set[pair_address]
        # Categories: "newPairs", "finalStretch", "migrated"
        self.categories: Dict[str, set] = {
            "newPairs": set(),
            "finalStretch": set(),
            "migrated": set()
        }
        # Optional callbacks for events
        self.on_update: Optional[Callable[[PulseToken], None]] = None
        self.on_new_token: Optional[Callable[[PulseToken], None]] = None
        self.on_token_removed: Optional[Callable[[str, str], None]] = None  # (category, pair_address)

    async def process_message(self, data: Any) -> None:
        """Process an incoming raw MessagePack message"""
        if not isinstance(data, (list, tuple)) or len(data) == 0:
            return

        msg_type = data[0]

        try:
            if msg_type == 0:
                self._handle_snapshot(data)
            elif msg_type == 1:
                self._handle_update(data)
            elif msg_type == 2:
                self._handle_new_token(data)
            elif msg_type == 3:
                self._handle_remove(data)
            else:
                logger.debug(f"Unknown message type: {msg_type}")
        except Exception as e:
            logger.error(f"Error processing Pulse message: {e}")

##### UNUSED FOR NOW #####
    async def process_json_message(self, data: Any) -> None:
        """Process incoming JSON message (e.g. newPairs)"""
        # handler.py sends [content] (list of tokens)
        if isinstance(data, list):
            count = 0
            for token_data in data:
                try:
                    token = self.decoder.from_dict(token_data)
                    
                    # Assign category
                    token.category = "newPairs"
                    
                    # Store logic
                    is_new = token.pair_address not in self.tokens
                    self.tokens[token.pair_address] = token
                    
                    # Assume JSON new_pairs implies "newPairs" category
                    # But if we want to be safe, we check if it's already in finalStretch?
                    # Generally newPairs JSON are strictly for the 'newPairs' room.
                    self.categories["newPairs"].add(token.pair_address)
                    
                    if is_new and self.on_new_token:
                        # For JSON tokens, we might want to flag them differently?
                        # No, a token is a token.
                        self.on_new_token(token)
                    
                    # If it parses well, trigger on_update too? 
                    # If it's effectively an update for an existing token.
                    if not is_new and self.on_update:
                        self.on_update(token)
                        
                    count += 1
                except Exception as e:
                    logger.error(f"Error parsing JSON token: {e}")
            
            if count > 0:
                logger.debug(f"Processed {count} JSON tokens")

    def _handle_snapshot(self, data: List[Any]) -> None:
        """Handle Type 0 Snapshot: Replaces or merges current state"""
        result = self.decoder.parse_snapshot(data)
        
        count = 0
        for category, tokens in result.items():
            new_set = set()
            
            for token in tokens:
                # Check if this is a new discovery
                is_new = token.pair_address not in self.tokens
                
                # Assign category to token
                token.category = category
                
                # Update storage
                self.tokens[token.pair_address] = token
                new_set.add(token.pair_address)
                count += 1
                
                # Trigger "New Token" event
                if is_new and self.on_new_token:
                    try:
                        self.on_new_token(token)
                    except Exception as e:
                        logger.error(f"Error in on_new_token callback: {e}")
            
            if category:
                self.categories[category] = new_set
                
        logger.debug(f"Processed snapshot: {count} tokens tracked")

    def _handle_update(self, data: List[Any]) -> None:
        """Handle Type 1 Update: Apply delta to existing token"""
        # [1, "pair_address", [[field_id, value], ...]]
        token = self.decoder.parse_update(data, self.tokens)
        
        if token:
            # Trigger callback if registered
            if self.on_update:
                try:
                    self.on_update(token)
                except Exception as e:
                    logger.error(f"Error in on_update callback: {e}")

    def _handle_new_token(self, data: List[Any]) -> None:
        """Handle Type 2 New Token: Full token data for newly monitored token"""
        result = self.decoder.parse_new_token(data)
        
        if not result:
            logger.warning("Failed to parse Type 2 message")
            return
            
        category, token = result
        
        # Check if this is truly new
        is_new = token.pair_address not in self.tokens
        
        # Assign category to token
        token.category = category
        
        # Add to storage
        self.tokens[token.pair_address] = token
        
        # Add to appropriate category
        if category in self.categories:
            self.categories[category].add(token.pair_address)
        
        logger.debug(f"Type 2: Added {token.name} ({token.ticker}) to {category}")
        
        # Trigger new token callback
        if is_new and self.on_new_token:
            try:
                self.on_new_token(token)
            except Exception as e:
                logger.error(f"Error in on_new_token callback: {e}")

    def _handle_remove(self, data: List[Any]) -> None:
        """Handle Type 3 Remove Token: Explicit removal notification"""
        result = self.decoder.parse_remove(data)
        
        if not result:
            logger.warning("Failed to parse Type 3 message")
            return
            
        category, pair_address = result
        
        # Check if token exists
        token_existed = pair_address in self.tokens
        
        # Remove from storage
        if pair_address in self.tokens:
            del self.tokens[pair_address]
        
        # Remove from category
        if category in self.categories:
            self.categories[category].discard(pair_address)
        
        logger.debug(f"Type 3: Removed {pair_address[:20]}... from {category}")
        
        # Trigger removal callback
        if token_existed and self.on_token_removed:
            try:
                self.on_token_removed(category, pair_address)
            except Exception as e:
                logger.error(f"Error in on_token_removed callback: {e}")

    def get_token(self, pair_address: str) -> Optional[PulseToken]:
        """Get a specific token by address"""
        return self.tokens.get(pair_address)

    def get_all_tokens(self) -> List[PulseToken]:
        """Get list of all tracked tokens, sorted by created_at desc (newest first)"""
        try:
            return sorted(
                self.tokens.values(),
                key=lambda x: x.created_at if x.created_at else "",
                reverse=True
            )
        except Exception:
            return list(self.tokens.values())

    def get_tokens_by_category(self, category: str) -> List[PulseToken]:
        """Get tokens for a specific category (e.g. finalStretch)"""
        addresses = self.categories.get(category, set())
        # Filter out any that might have been deleted from main dict (unlikely but safe)
        return [self.tokens[addr] for addr in addresses if addr in self.tokens]

    def get_final_stretch_tokens(self) -> List[PulseToken]:
        """Filter for likely Final Stretch tokens (logic dependent on how we identify them)"""
        return self.get_tokens_by_category("finalStretch")
