from typing import List, Tuple
from datetime import datetime, timezone
import logging
from src.pulse.types import PulseToken, TradeResult, TokenState
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig

logger = logging.getLogger(__name__)

class BaselineBuyRulesMixin:
    """Mixin for strategy buy signaling and momentum rules"""
    
    config: BaselineStrategyConfig

    def _pass_buy_rules_checkup(self, token: PulseToken, past_trades_on_token: List[TradeResult], sol_price: float) -> bool:
        """Check for buy signal related to basic limits and bounds"""
        # Check Trade Limits
        if len(past_trades_on_token) >= self.config.risk.max_trades_per_token:
            return False

        if past_trades_on_token:
            last_trade = past_trades_on_token[-1]
            time_since_sell = (datetime.now(timezone.utc) - last_trade.time_sold).total_seconds() / 60
            if time_since_sell < self.config.risk.cooldown_minutes:
                return False

        # Check token age 
        if token.created_at:
            try:
                created_time = datetime.fromisoformat(token.created_at.replace('Z', '+00:00'))
                age_seconds = (datetime.now(timezone.utc) - created_time).total_seconds()
                if age_seconds > self.config.buy_rules.max_token_age_seconds:
                    return False
            except Exception:
                pass  # If parsing fails, skip age check
                
        if token.market_cap * sol_price < self.config.buy_rules.min_market_cap:
            return False
            
        if token.market_cap * sol_price > self.config.buy_rules.max_market_cap:
            return False
            
        return True

    def _calculate_momentum(self, state: TokenState) -> Tuple[bool, str]:
        """
        Calculate momentum metrics for baseline entry.
        Returns (True, "reason") if momentum is sufficient, else (False, "reason").
        """
        token = state.token
        snapshots = state.snapshots
        
        target_time_seconds = self.config.buy_rules.activity_lookback_seconds
        
        txns_last_minute = 0
        buys_last_minute = 0
        sells_last_minute = 0
        users_watching_increase = 0
        
        if len(snapshots) >= 2:
            current = snapshots[-1]
            
            # Find the closest snapshot to ~60s ago
            now = current.timestamp
            past_snapshot = snapshots[0] # Default to oldest available
            
            for s in reversed(snapshots):
                delta = (now - s.timestamp).total_seconds()
                if delta >= target_time_seconds:
                    past_snapshot = s
                    break

            txns_last_minute = current.txns - past_snapshot.txns
            buys_last_minute = current.buys - past_snapshot.buys
            sells_last_minute = current.sells - past_snapshot.sells
            
            # Smooth active users watching via moving average (+/- 10s window around target points)
            now_ts = now.timestamp()
            recent_snaps = [s.users_watching for s in snapshots if s.timestamp.timestamp() >= now_ts - 10.0]
            current_users_vals = recent_snaps + [token.active_users_watching]
            current_users_ma = sum(current_users_vals) / len(current_users_vals)
            
            past_ts = past_snapshot.timestamp.timestamp()
            old_window_snaps = [s.users_watching for s in snapshots if abs(s.timestamp.timestamp() - past_ts) <= 10.0]
            if old_window_snaps:
                old_users_ma = sum(old_window_snaps) / len(old_window_snaps)
            else:
                old_users_ma = past_snapshot.users_watching

            users_watching_increase = current_users_ma - old_users_ma
        else:
            return False, "Not enough snapshot history to measure momentum"
            
        if txns_last_minute < self.config.buy_rules.min_txns_per_min:
            return False, f"Not enough txns ({txns_last_minute} < {self.config.buy_rules.min_txns_per_min})"
            
        if sells_last_minute > 0:
            buy_sell_ratio = buys_last_minute / sells_last_minute
        else:
            buy_sell_ratio = buys_last_minute # Infinity effectively
            
        if buy_sell_ratio < self.config.buy_rules.min_buy_sell_ratio:
            return False, f"Low buy/sell ratio ({buy_sell_ratio:.2f} < {self.config.buy_rules.min_buy_sell_ratio})"
            
        # 3. Users Watching
        if users_watching_increase < self.config.buy_rules.min_users_watching_increase:
            return False, f"Not enough users watching increase ({users_watching_increase} < {self.config.buy_rules.min_users_watching_increase})"
            
        return True, "Momentum requirements met"
