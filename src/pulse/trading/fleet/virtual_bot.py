import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone

from src.pulse.types import SharedTokenState, TradeTakenInformation, SellReason, TokenState, TradeResult, PulseToken, SellCategory, BotGlobalState
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.pulse.trading.fleet.shadow_recorder import ShadowRecorder, ShadowTradeRecord
from src.pulse.trading.strategies.core_strategy import CoreStrategy

logger = logging.getLogger("VirtualBot")

class VirtualBot:
    """
    A lightweight virtual trading bot.
    - Has its own Strategy Configuration.
    - Manages its own active trades.
    - Uses SharedTokenState for market data.
    """
    
    def __init__(self, name: str, config: Any, recorder: ShadowRecorder, strategy_type: str = "core"):
        self.strategy_id = name
        self.config = config
        self.recorder = recorder
        self.strategy_type = strategy_type
        
        # Internal State: PairAddress -> TradeTakenInformation
        self.active_positions: Dict[str, TradeTakenInformation] = {}
        self.past_trades: Dict[str, List[TradeResult]] = {}

        self.global_state = BotGlobalState(
            current_balance=config.account.starting_balance,
            max_allowed_drawdown= -(config.account.starting_balance * 0.50) # 50% fail fast, hardcoded for now
        )
        self.is_dead = False

        # Store Safety Score for each PairAddress -> float (because it is dependent on the strategy)
        self.holder_safety_score: Dict[str, float] = {}

        self._current_sol_price = 0.0

        # Initialize Strategy
        if self.strategy_type == "baseline":
            from src.pulse.trading.strategies.baseline_strategy.baseline_strategy_main import BaselineStrategy
            self.strategy = BaselineStrategy(
                config=self.config, get_sol_price=lambda: self._current_sol_price)
        else:
            self.strategy = CoreStrategy(
                config=self.config, get_sol_price=lambda: self._current_sol_price)

    def process_update(self, shared_state: SharedTokenState, sol_price: float):
        """
        Process a token update from the Manager.
        """
        self._current_sol_price = sol_price
        
        # 1. Check if we are already holding this pair
        if shared_state.token.pair_address in self.active_positions:
            self._manage_active_trade(shared_state)
        else:
            # We scan for entry on updates too (in case it meets criteria later)
            self._scan_for_entry(shared_state)

    def process_new_token(self, shared_state: SharedTokenState):
        """
        Called EXACTLY once per token, AFTER initial heavy data (holders, ath) is fetched.
        """
        self._calculate_safety_score(shared_state)
        self._scan_for_entry(shared_state)

    def process_token_removed(self, pair_address: str, category: str, latest_market_cap_usd: float, shared_state: SharedTokenState = None):
        """Force close if we hold it"""
        trade = self.active_positions.get(pair_address)
        if trade:
            logger.debug("[%s] Force closing %s (Removed from %s)", self.strategy_id, pair_address, category)
            #Update the market cap to the latest market cap
            trade.current_market_cap = latest_market_cap_usd
            self.active_positions[pair_address] = trade
            self._execute_virtual_sell(
                trade,
                SellReason(category=SellCategory.TOKEN_REMOVED, details=f"Removed from {category}"),
                shared_state
            )

    def _scan_for_entry(self, shared_state: SharedTokenState):
        """Check if we should enter a trade"""
        # If bot hit max drawdown, it shouldn't trade anymore
        if getattr(self, "is_dead", False):
            return
            
        # If we don't have price, we can't evaluate MC-based rules
        if self._current_sol_price <= 0:
            return

        # Create a temporary 'TokenState' view for the strategy
        temp_state = self._create_strategy_state(shared_state)
        
        # Run Strategy
        should_buy, position_size, confidence = self.strategy.should_buy(temp_state)
        
        if should_buy:
            self._execute_virtual_buy(shared_state.token, position_size, confidence)

    def _manage_active_trade(self, shared_state: SharedTokenState):
        """Check if we should exit a trade"""
        if self._current_sol_price <= 0:
            return

        pair_address = shared_state.token.pair_address
        trade = self.active_positions[pair_address]

        # Update current_market_cap with the latest price tick.
        # token_snapshot is NEVER touched — it stays frozen at buy time.
        current_mc_usd = shared_state.token.market_cap * self._current_sol_price
        trade.current_market_cap = current_mc_usd
        trade.current_curve_pct = shared_state.token.bonding_curve_percentage
        updated_trade = trade
        self.active_positions[pair_address] = updated_trade

        strategy_state = self._create_strategy_state(shared_state)
        strategy_state.active_trade = updated_trade
        sell_reason = self.strategy.should_sell(updated_trade, strategy_state)
        if sell_reason:
            self._execute_virtual_sell(updated_trade, sell_reason, shared_state)
            self._check_drawdown_limit()

    def _check_drawdown_limit(self):
        """Check if the bot's portfolio has dropped below the fail-fast limit."""
        if getattr(self, "is_dead", False):
            return
        
        if self.global_state.total_pnl <= self.global_state.max_allowed_drawdown:
            logger.warning(f"💀 [FAIL FAST] Bot {self.strategy_id} hit max drawdown limit ({self.global_state.total_pnl:.2f} SOL). Killing bot.")
            self.is_dead = True
            # Force close any remaining open trades
            self.shutdown()

    def _execute_virtual_buy(self, token: PulseToken, position_size: float, confidence: float):
        market_cap_usd = token.market_cap * self._current_sol_price
        
        # Log
        logger.debug("[%s] 🟢 BUY %s @ $%s MC (Confidence: %.2f)", self.strategy_id, token.ticker, f"{token.market_cap:,.0f}", confidence)
        
        # Record Trade
        trade = TradeTakenInformation(
            token_bought_snapshot=token,
            buy_market_cap=market_cap_usd,
            time_bought=datetime.now(timezone.utc),
            current_market_cap=market_cap_usd,
            current_curve_pct=token.bonding_curve_percentage,
            position_size=position_size,
            confidence=confidence,
        )
        self.active_positions[token.pair_address] = trade

    def calculate_fees(self, amount: float) -> float:
        """Calculate fees based on configured percentage"""
        # Access nested config for fees_percentage
        fee_pct = self.config.account.fees_percentage
        return amount * fee_pct

    def _execute_virtual_sell(self, trade: TradeTakenInformation, reason: SellReason, shared_state: SharedTokenState = None):
        """
        All sell data lives on the trade:
          trade.token_bought_snapshot   — buy-time token, for logs/CSV
          trade.current_market_cap — latest MC (updated each tick)
        """
        snapshot = trade.token_bought_snapshot
        exit_mc_usd = trade.current_market_cap
        entry_mc_usd = trade.buy_market_cap
        pair_address = snapshot.pair_address
        
        # Calculate Position Value & PnL with Fees
        # 1. Entry
        position_size = trade.position_size
        buy_fees = self.calculate_fees(position_size)
        initial_cost = position_size + buy_fees
        
        # 2. Exit
        # Proportional value change based on MC change
        if entry_mc_usd > 0:
            value_ratio = exit_mc_usd / entry_mc_usd
        else:
            value_ratio = 0.0
            
        gross_exit_value = position_size * value_ratio
        sell_fees = self.calculate_fees(gross_exit_value)
        net_exit_value = gross_exit_value - sell_fees
        
        # 3. Net Profit
        net_profit = net_exit_value - initial_cost
        total_fees = buy_fees + sell_fees
        
        # ROI %
        pnl_percent = 0.0
        if initial_cost > 0:
            pnl_percent = (net_profit / initial_cost) * 100
            
        # Update Global State
        self.global_state.total_trades += 1
        self.global_state.total_pnl += net_profit
        self.global_state.current_balance += net_profit
        if net_profit > 0:
            self.global_state.winning_trades += 1
        self.global_state.win_rate = (self.global_state.winning_trades / self.global_state.total_trades) * 100
            
        duration = (datetime.now(timezone.utc) - trade.time_bought).total_seconds()
        
        logger.debug("[%s] 🔴 SELL %s | PnL: %+.2f%% (Net: %+.4f SOL) | Fees: %.4f | Reason: %s",
                    self.strategy_id, snapshot.ticker, pnl_percent, net_profit, total_fees, reason.category)
        
        # Log to db via Recorder
        # We need to grab the latest DB Snapshot ID directly from the shared state
        snapshot_id = getattr(shared_state, 'latest_db_snapshot_id', None) if shared_state else None
        if snapshot_id is None:
            logger.warning("⚠️ No snapshot ID found while selling %s", snapshot.ticker)
        
        record = ShadowTradeRecord(
            strategy_id=self.strategy_id,
            token_symbol=snapshot.ticker,
            token_address=snapshot.token_address,
            entry_price=entry_mc_usd,
            exit_price=exit_mc_usd,
            pnl_percent=pnl_percent,
            profit=net_profit,
            fees_paid=total_fees,
            duration_seconds=duration,
            exit_reason=f"{reason.category}: {reason.details}",
            entry_confidence=trade.confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sell_snapshot_id=snapshot_id
        )
        
        self.recorder.log_trade(record)

        # Store Past Trade
        result = TradeResult(
            pair_address=pair_address,
            token_ticker=snapshot.ticker,
            token_name=snapshot.name,
            profit=net_profit,
            fees_paid=total_fees,
            sell_reason=reason,
            time_bought=trade.time_bought,
            time_sold=datetime.now(timezone.utc),
            buy_market_cap=entry_mc_usd,
            sell_market_cap=exit_mc_usd,
            position_size=position_size
        )

        if pair_address not in self.past_trades:
            self.past_trades[pair_address] = []
        self.past_trades[pair_address].append(result)

        # Cleanup
        if pair_address in self.active_positions:
            del self.active_positions[pair_address]

    def shutdown(self, shared_tokens: Dict[str, SharedTokenState] = None):
        """Shutdown resources"""
        logger.debug("Virtual Bot %s shutting down. All trades are being sold...", self.strategy_id)
        for trade in list(self.active_positions.values()):
            shared_state = shared_tokens.get(trade.token_bought_snapshot.pair_address)
            self._execute_virtual_sell(trade, SellReason(category=SellCategory.SHUTDOWN), shared_state)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _calculate_safety_score(self, shared: SharedTokenState):
        """Calculate and cache safety score once"""
        if shared.raw_holders:
            temp_state = TokenState(token=shared.token)
            self.strategy.check_holder_safety(temp_state, shared.raw_holders)
            if temp_state.holder_safety_score is not None:
                self.holder_safety_score[shared.token.pair_address] = temp_state.holder_safety_score

    def _create_strategy_state(self, shared: SharedTokenState) -> TokenState:
        """
        Convert SharedTokenState -> TokenState (Private View) with local Safety Check
        """
        pair_address = shared.token.pair_address
        
        # 1. Resolve Safety Score (Cached)
        # Pre-calculated in process_new_token
        # If we don't have a score, default 0.5
        safety_score = self.holder_safety_score.get(pair_address, 0.5)

        # 2. Basic Mapping
        state = TokenState(
            token=shared.token,
            # active_trade is None for scanning context
            past_trades=self.past_trades.get(pair_address, []),
            ath_market_cap=shared.ath_market_cap,
            snapshots=shared.snapshots,
            last_snapshot_time=shared.last_snapshot_time,
            holder_safety_score=safety_score
        )
            
        return state
