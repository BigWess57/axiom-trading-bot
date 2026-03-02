from typing import Callable, Optional, Tuple
from datetime import datetime, timezone
import logging

from src.pulse.types import SellReason, SellCategory, TradeTakenInformation, TokenState
from src.pulse.trading.strategies.strategy_models import StrategyConfig
from src.pulse.trading.strategies.mixins.security_mixin import SecurityMixin
from src.pulse.trading.strategies.mixins.risk_mixin import RiskMixin
from src.pulse.trading.strategies.mixins.buy_rules_mixin import BuyRulesMixin
from src.pulse.trading.strategies.mixins.confidence_mixin import ConfidenceMixin

logger = logging.getLogger(__name__)

class CoreStrategy(SecurityMixin, RiskMixin, BuyRulesMixin, ConfidenceMixin):
    """
    Core trading strategy acting as the main orchestrator.
    Logic is delegated to mixins.
    """
    
    def __init__(self, config: StrategyConfig, get_sol_price: Callable[[], float]):
        """
        Initialize strategy with configuration
        
        Args:
            config: Strategy configuration (stop_loss_pct, take_profit_pct)
            get_sol_price: Callable that returns current SOL price
        """
        self.config = config
        self.get_sol_price = get_sol_price
    
    def should_buy(self, state: TokenState) -> Tuple[bool, float, float]:
        """Evaluate if we should buy this token. Returns (should_buy, position_size, confidence)"""
        token = state.token
        past_trades_on_token = state.past_trades
        
        sol_price = self.get_sol_price()
        if sol_price <= 0:
            logger.debug(f"Waiting for SOL price to evaluate tokens.")
            return False, 0.0, 0.0

        if token.category != "finalStretch":
            logger.info(f"Token not in finalStretch ({token.ticker}). Not interested for now.")
            return False, 0.0, 0.0

        security_issue = self._security_checkup(token, sol_price)
        if security_issue:
            return False, 0.0, 0.0

        if not self._pass_buy_rules_checkup(token, past_trades_on_token, sol_price):
            return False, 0.0, 0.0
            
        confidence = self._calculate_buy_confidence(state, sol_price)

        min_confidence_for_buy = self.config.confidence.min_confidence_score
        max_score = self.config.confidence.good_confidence_score

        if confidence < min_confidence_for_buy:
            return False, 0.0, 0.0

        if confidence >= max_score:
            position_size = self.config.risk.max_position_size
        else:
            ratio = (confidence - min_confidence_for_buy) / (max_score - min_confidence_for_buy)
            position_size = self.config.risk.min_position_size + ratio * (self.config.risk.max_position_size - self.config.risk.min_position_size)

        logger.info(f"SHOULD BUY signal for {token.ticker} with confidence {confidence:.2f} (Size: {position_size:.3f} SOL)")
        return True, position_size, confidence
    
    def should_sell(self, trade_info: TradeTakenInformation, state: TokenState) -> Optional[SellReason]:
        """Evaluate if we should sell this token"""
        token = trade_info.token_bought_snapshot
        
        sol_price = self.get_sol_price()
        if sol_price <= 0:
            return None

        if token.category != "finalStretch":
            logger.info(f"Token not in finalStretch ({token.ticker}). Selling.")
            return SellReason(
                category=SellCategory.CATEGORY_CHANGE,
                details=f"Token moved from finalStretch to {token.category}"
            )

        security_issue = self._security_checkup(token, sol_price)
        if security_issue:
            return SellReason(
                category=SellCategory.SECURITY_FAILED,
                details=security_issue
            )

        sl_tp_reason = self._check_for_sl_tp(trade_info)
        if sl_tp_reason:
            return sl_tp_reason
            
        hold_trade_confidence = self._calculate_hold_confidence(state, sol_price)
        if hold_trade_confidence < self.config.hold_confidence.min_hold_confidence_score:
            return SellReason(
                category=SellCategory.LOW_CONFIDENCE,
                details=f"Hold confidence {hold_trade_confidence:.2f} is too low"
            )

        if (datetime.now(timezone.utc) - trade_info.time_bought).total_seconds() > self.config.risk.max_holding_time:
            hold_time_minutes = self.config.risk.max_holding_time / 60
            logger.info(f"Max holding time of {hold_time_minutes} minutes for {token.ticker} reached. Selling.")
            return SellReason(
                category=SellCategory.MAX_HOLD_TIME,
                details=f"Held for {hold_time_minutes:.1f} minutes"
            )
        
        return None
