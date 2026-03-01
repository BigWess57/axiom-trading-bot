from typing import Optional
import logging
from src.pulse.types import SellReason, SellCategory, TradeTakenInformation
from src.pulse.trading.strategies.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)

class RiskMixin:
    """Mixin for strategy risk checking (stop loss, take profit)"""
    
    config: StrategyConfig

    def _check_for_sl_tp(self, trade_info: TradeTakenInformation) -> Optional[SellReason]:
        """Check for stop loss or take profit"""
        ticker = trade_info.token_bought_snapshot.ticker
        current_mc_usd = trade_info.current_market_cap
        buy_market_cap = trade_info.buy_market_cap
        
        # Check Curve Graduation
        if trade_info.current_curve_pct >= self.config.risk.sell_at_curve_pct * 100:
            logger.info(f"Token {ticker} reached bonding curve limit ({trade_info.current_curve_pct}%). Selling.")
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Curve Completion: Hit {trade_info.current_curve_pct}% (Target: {self.config.risk.sell_at_curve_pct * 100}%)"
            )

        if current_mc_usd < buy_market_cap * (1 - self.config.risk.stop_loss_pct):
            logger.info(f"Token {ticker} has reached stop loss.")
            loss_pct = ((buy_market_cap - current_mc_usd) / buy_market_cap) * 100
            return SellReason(
                category=SellCategory.STOP_LOSS,
                details=f"Down {loss_pct:.1f}% from entry (${buy_market_cap:.0f} => ${current_mc_usd:.0f})"
            )

        if current_mc_usd > buy_market_cap * (1 + self.config.risk.take_profit_pct):
            logger.info(f"Token {ticker} has reached take profit.")
            profit_pct = ((current_mc_usd - buy_market_cap) / buy_market_cap) * 100
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Up {profit_pct:.1f}% from entry (${buy_market_cap:.0f} => ${current_mc_usd:.0f})"
            )

        return None
