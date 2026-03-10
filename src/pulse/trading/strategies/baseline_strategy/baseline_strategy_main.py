import logging
from typing import Tuple, Optional, Callable
from datetime import datetime, timezone

from src.pulse.types import SellReason, TokenState, TradeTakenInformation, SellCategory
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig
from src.pulse.trading.strategies.baseline_strategy.mixins.baseline_security_mixin import BaselineSecurityMixin
from src.pulse.trading.strategies.baseline_strategy.mixins.baseline_buy_rules_mixin import BaselineBuyRulesMixin
from src.pulse.trading.strategies.baseline_strategy.mixins.baseline_risk_mixin import BaselineRiskMixin

logger = logging.getLogger(__name__)

class BaselineStrategy(BaselineSecurityMixin, BaselineBuyRulesMixin, BaselineRiskMixin):
    """
    The main orchestrator for the simplified Baseline Scalper logic.
    """
    def __init__(self, config: BaselineStrategyConfig, get_sol_price: Callable[[], float]):
        self.config = config
        self.get_sol_price = get_sol_price

    def should_buy(self, state: TokenState) -> Tuple[bool, float, float]:
        """
        Evaluate if a token should be bought based on strict security and raw momentum.
        Returns (should_buy: bool, position_size: float, confidence_score: float)
        """
        sol_price = self.get_sol_price()
        if sol_price <= 0:
            return False, 0.0, 0.0

        token = state.token
        
        # 1. Security Checkup
        security_issue = self._security_checkup(token, sol_price, state.holder_safety_score)
        if security_issue:
            logger.debug(f"[Baseline] Rejecting {token.ticker}: {security_issue}")
            return False, 0.0, 0.0

        # 2. Basic Rules Check (Age, MC Limits, Trade limits)
        if not self._pass_buy_rules_checkup(token, state.past_trades, sol_price):
            return False, 0.0, 0.0

        # 3. Momentum Check
        has_momentum, momentum_reason = self._calculate_momentum(state)
        if not has_momentum:
            logger.debug(f"[Baseline] Rejecting {token.ticker}: {momentum_reason}")
            return False, 0.0, 0.0

        # All checks passed! 
        # Return True, Fixed Position Size, and a placeholder confidence score of 50.0
        logger.debug(f"[Baseline] ✨ BUY SIGNAL FOR {token.ticker} - Momentum matched!")
        return True, self.config.risk.max_position_size, 50.0

    def should_sell(self, trade_info: TradeTakenInformation, state: TokenState) -> Optional[SellReason]:
        """
        Evaluate fixed exit conditions.
        """
        token = trade_info.token_bought_snapshot
        
        # Check max holding time
        if (datetime.now(timezone.utc) - trade_info.time_bought).total_seconds() > self.config.risk.max_holding_time:
            hold_time_minutes = self.config.risk.max_holding_time / 60
            logger.debug(f"Max holding time of {hold_time_minutes} minutes for {token.ticker} reached. Selling.")
            return SellReason(
                category=SellCategory.MAX_HOLD_TIME,
                details=f"Held for {hold_time_minutes:.1f} minutes"
            )
        
        # Check for SL/TP
        sell_reason = self._check_for_sl_tp(trade_info)
        if sell_reason is not None:
            return sell_reason
        
        return None

