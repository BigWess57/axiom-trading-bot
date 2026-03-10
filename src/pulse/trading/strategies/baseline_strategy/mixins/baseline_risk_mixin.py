from typing import Optional
import logging
from src.pulse.types import SellReason, SellCategory, TradeTakenInformation
from src.pulse.trading.strategies.baseline_strategy.baseline_models import BaselineStrategyConfig

logger = logging.getLogger(__name__)

class BaselineRiskMixin:
    """Mixin for strategy risk checking (stop loss, take profit)"""
    
    config: BaselineStrategyConfig

    def _check_for_sl_tp(self, trade_info: TradeTakenInformation) -> Optional[SellReason]:
        """Check for strictly fixed stop loss or take profit"""
        ticker = trade_info.token_bought_snapshot.ticker
        current_mc_usd = trade_info.current_market_cap
        buy_market_cap = trade_info.buy_market_cap
        
        # Check Curve Graduation
        if trade_info.current_curve_pct >= self.config.risk.sell_at_curve_pct * 100:
            logger.debug(f"Token {ticker} reached bonding curve limit ({trade_info.current_curve_pct}%). Selling.")
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Curve Completion: Hit {trade_info.current_curve_pct}% (Target: {self.config.risk.sell_at_curve_pct * 100}%)"
            )

        # Baseline SL/TP
        stop_loss_mc = buy_market_cap * (1 - self.config.risk.initial_stop_loss_pct)
        take_profit_mc = buy_market_cap * (1 + self.config.risk.max_take_profit_pct)

        if current_mc_usd < stop_loss_mc:
            logger.debug(f"Token {ticker} triggered Stop Loss.")
            loss_pct = ((current_mc_usd - buy_market_cap) / buy_market_cap) * 100
            
            return SellReason(
                category=SellCategory.STOP_LOSS,
                details=f"Fixed Stop Loss: Out at ${current_mc_usd:.0f} (Entry: ${buy_market_cap:.0f}, {loss_pct:+.1f}%)"
            )

        if current_mc_usd > take_profit_mc:
            logger.debug(f"Token {ticker} has reached take profit {self.config.risk.max_take_profit_pct*100:.1f}%.")
            profit_pct = ((current_mc_usd - buy_market_cap) / buy_market_cap) * 100
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Fixed Take Profit: Up {profit_pct:.1f}% from entry (${buy_market_cap:.0f} => ${current_mc_usd:.0f})"
            )

        return None
