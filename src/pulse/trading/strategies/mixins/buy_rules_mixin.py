from typing import List
from datetime import datetime, timezone
from src.pulse.types import PulseToken, TradeResult
from src.pulse.trading.strategies.strategy_models import StrategyConfig

class BuyRulesMixin:
    """Mixin for strategy buy signaling rules"""
    
    config: StrategyConfig

    def _pass_buy_rules_checkup(self, token: PulseToken, past_trades_on_token: List[TradeResult], sol_price: float) -> bool:
        """Check for buy signal"""
        # Check Trade Limits
        if len(past_trades_on_token) >= self.config.risk.max_trades_per_token:
            return False

        if past_trades_on_token:
            last_trade = past_trades_on_token[-1]
            time_since_sell = (datetime.now(timezone.utc) - last_trade.time_sold).total_seconds() / 60
            if time_since_sell < self.config.risk.cooldown_minutes:
                return False

        # Check token age (max 10 minutes old)
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
        # if token.volume_total < token.market_cap:
        #     return False
        
        return True
