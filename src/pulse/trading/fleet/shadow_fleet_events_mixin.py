import asyncio
import logging
from datetime import datetime, timezone
from src.pulse.types import PulseToken, SharedTokenState

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetEventsMixin:
    """Mixin tracking token lifecycle operations and triggering bot execution events."""

    def update_sol_price(self, price: float):
        """Update SOL price globally."""
        self.current_sol_price = price

    async def on_token_update(self, token: PulseToken):
        """Multicast Update"""
        logger.debug(f"Processing update for token: {token.ticker}")
        
        # 1. Manage Shared State
        if token.pair_address not in self.shared_tokens:
            self.shared_tokens[token.pair_address] = SharedTokenState(token=token)
            
        state = self.shared_tokens[token.pair_address]
        
        # Fallback trigger if 'update' arrived before 'new_token'
        if not state.is_fetching_data:
            state.is_fetching_data = True
            asyncio.create_task(self._process_new_token_workflow(token, state))
            
        # Wait safely for the JS Chromium payload to finish gathering holders/chart if still initializing
        await state.init_event.wait()
        
        state.token = token # Update latest data
        
        # 2. Enhance State (Snapshot, ATH)
        # Record internal array snapshot
        self._record_snapshot(token, state)
        
        # Record to SQLite Database
        self._record_db_snapshot(token, state)
        
        # Check ATH
        current_mc_usd = token.market_cap * getattr(self, "current_sol_price", 0.0)
        state.ath_market_cap = max(state.ath_market_cap, current_mc_usd)
        
        # 3. Broadcast to Fleet
        for bot in getattr(self, "bots", []):
            try:
                bot.process_update(state, getattr(self, "current_sol_price", 0.0))
            except Exception as e:
                logger.error(f"Error in Bot {bot.strategy_id}: {e}")

    async def on_new_token(self, token: PulseToken):
        """Handle new token discovery"""
        logger.info(f"🆕 New Token: {token.ticker}")
        
        if token.pair_address not in self.shared_tokens:
            self.shared_tokens[token.pair_address] = SharedTokenState(token=token)
            # Log exact immutable token data to DB exactly once upon discovery
            if hasattr(self, "recorder"):
                self.recorder.log_token(token)
            
        state = self.shared_tokens[token.pair_address]
        
        # Sequentially fetch data (Async to avoid blocking WS loop, but we must AWAIT inside the task)
        if not state.is_fetching_data:
            state.is_fetching_data = True
            asyncio.create_task(self._process_new_token_workflow(token, state))

    async def _process_new_token_workflow(self, token: PulseToken, state: SharedTokenState):
        """
        Background workflow:
        1. Fetch JS Full Analysis (Chart & Holders concurrently in V8)
        2. Call bot.process_new_token
        """
        if getattr(self, "client", None):
            if getattr(self, "baseline_mode", False):
                await self._fetch_holder_data(token, state)
            else:
                await self._fetch_full_token_data(token, state)
        
        # Ensure an initial DB snapshot exists *before* bots potentially buy it
        self._record_db_snapshot(token, state)
        
        # Now that state is populated, notify bots
        for bot in getattr(self, "bots", []):
            try:
                bot.process_new_token(state)
            except Exception as e:
                logger.error(f"Error in Bot {bot.strategy_id} process_new_token: {e}")
                
        # Mark as officially initialized to unblock queued on_token_update events for this token
        state.init_event.set()

    async def on_token_removed(self, category: str, pair_address: str):
        """Handle token removal"""
        logger.info(f"❌ Token Removed: {pair_address}")
        token_state = getattr(self, "shared_tokens", {}).get(pair_address)
        if not token_state:
            logger.warning(f"Token {pair_address} not found in shared tokens")
            return
        
        latest_market_cap_usd = await self.get_latest_market_cap(pair_address, token_state.token.total_supply)
        if latest_market_cap_usd is None:
            logger.error(f"Failed to get latest market cap for {pair_address}. Using token_state.token.market_cap (might not be updated)")
            latest_market_cap_usd = token_state.token.market_cap * getattr(self, "current_sol_price", 0.0)
            
        for bot in getattr(self, "bots", []):
            bot.process_token_removed(pair_address, category, latest_market_cap_usd, token_state)
            
        # Remove token from state
        del self.shared_tokens[pair_address]
