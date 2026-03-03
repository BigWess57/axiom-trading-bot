from typing import Optional
import logging
from src.pulse.types import SellReason, SellCategory, TradeTakenInformation
from src.pulse.trading.strategies.strategy_models import StrategyConfig

logger = logging.getLogger(__name__)

class RiskMixin:
    """Mixin for strategy risk checking (stop loss, take profit)"""
    
    config: StrategyConfig

    def _check_for_sl_tp(self, trade_info: TradeTakenInformation, hold_trade_confidence: float) -> Optional[SellReason]:
        """Check for stop loss or take profit"""
        ticker = trade_info.token_bought_snapshot.ticker
        current_mc_usd = trade_info.current_market_cap
        buy_market_cap = trade_info.buy_market_cap
        
        # Track Peak Market Cap for Trailing Logic
        trade_info.peak_market_cap = max(trade_info.peak_market_cap, current_mc_usd)

        # Check Curve Graduation
        if trade_info.current_curve_pct >= self.config.risk.sell_at_curve_pct * 100:
            logger.info(f"Token {ticker} reached bonding curve limit ({trade_info.current_curve_pct}%). Selling.")
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Curve Completion: Hit {trade_info.current_curve_pct}% (Target: {self.config.risk.sell_at_curve_pct * 100}%)"
            )

        # Store fixed bounds on first tick if not set
        if trade_info.fixed_take_profit_pct is None:
            # 1. Determine Dynamic Bounds (Early vs Late Entry)
            # Pump.fun uses a virtual CPAMM: virtual_sol * virtual_token = k (32.19 billion)
            # We can precisely calculate the Market Cap (in SOL) at any point on the curve.
            # MC(SOL) = price_in_sol * total_supply
            # price_in_sol = virtual_sol / virtual_token
            # virtual_token = k / virtual_sol
            # Therefore: MC(SOL) = (virtual_sol^2 / k) * 1_000_000_000
            # Given we know Graduation occurs at ~85 Real SOL = 115 Virtual SOL.
            
            # We estimate current Virtual SOL from the Curve Percentage
            # curve_pct = (real_sol_added / 85.0)  --> real_sol_added = curve_pct * 85.0
            current_curve_ratio = trade_info.current_curve_pct / 100.0
            current_virtual_sol = 30.0 + (current_curve_ratio * 85.0)
            
            # Target Virtual SOL based on our config limit (e.g. 98% of curve)
            target_curve_ratio = self.config.risk.sell_at_curve_pct
            target_virtual_sol = 30.0 + (target_curve_ratio * 85.0)
            
            # Because MC is proportional to virtual_sol^2, the ratio of target MC to current MC 
            # is simply the ratio of their squared Virtual SOLs.
            target_mc_multiplier = (target_virtual_sol ** 2) / (current_virtual_sol ** 2) if current_virtual_sol > 0 else 1.0
            
            # The target market cap in USD is simply current_mc_usd * multiplier
            sell_target_mc = current_mc_usd * target_mc_multiplier
            
            max_possible_profit_pct = (sell_target_mc - buy_market_cap) / buy_market_cap
            
            if max_possible_profit_pct < self.config.risk.max_take_profit_pct:
                # LATE ENTRY
                trade_info.fixed_take_profit_pct = max_possible_profit_pct
                trade_info.fixed_stop_loss_pct = max_possible_profit_pct / self.config.risk.late_entry_rr_ratio
                logger.info(f"Late Entry on {ticker}: Fixed TP=+{trade_info.fixed_take_profit_pct*100:.1f}%, Fixed SL=-{trade_info.fixed_stop_loss_pct*100:.1f}%")
            else:
                # EARLY ENTRY (Runner)
                trade_info.fixed_take_profit_pct = self.config.risk.max_take_profit_pct
                # We do not fix SL for early entries, we use trailing logic
                trade_info.fixed_stop_loss_pct = None 
                logger.info(f"Early Entry on {ticker}: Max TP=+{trade_info.fixed_take_profit_pct*100:.1f}%. Trailing SL activated.")

        active_tp_pct = trade_info.fixed_take_profit_pct
        
        # 2. Calculate Active Stop Loss
        active_sl_mc = 0.0
        
        if trade_info.fixed_stop_loss_pct is not None:
            # We are in Late Entry Mode (Fixed SL)
            active_sl_mc = buy_market_cap * (1 - trade_info.fixed_stop_loss_pct)
        else:
            # We are in Early Entry Mode (Runner)
            # Baseline SL
            baseline_sl_mc = buy_market_cap * (1 - self.config.risk.initial_stop_loss_pct)
            
            # Confidence-Driven Trailing Step
            if hold_trade_confidence < self.config.risk.confidence_caution_threshold:
                # Weakness detected. Calculate a tight SL 20% behind the peak.
                trailing_sl_mc = trade_info.peak_market_cap * (1 - self.config.risk.trailing_step_buffer_pct)
                # Persist the highest trailing SL achieved permanently
                trade_info.highest_trailing_sl_mc = max(trade_info.highest_trailing_sl_mc, trailing_sl_mc)
                
            # Active SL is the highest of baseline or any previously locked-in trailing SL
            active_sl_mc = max(baseline_sl_mc, trade_info.highest_trailing_sl_mc)

        # 3. Execute Checks
        if current_mc_usd < active_sl_mc:
            logger.info(f"Token {ticker} triggered Stop Loss.")
            loss_pct = ((current_mc_usd - buy_market_cap) / buy_market_cap) * 100
            
            # Add detail if it was trailing
            detail_prefix = "Trailing " if (trade_info.fixed_stop_loss_pct is None and active_sl_mc > buy_market_cap) else ""
            
            return SellReason(
                category=SellCategory.STOP_LOSS,
                details=f"{detail_prefix}Stop Loss: Out at ${current_mc_usd:.0f} (Entry: ${buy_market_cap:.0f}, {loss_pct:+.1f}%)"
            )

        if current_mc_usd > buy_market_cap * (1 + active_tp_pct):
            logger.info(f"Token {ticker} has reached take profit {active_tp_pct*100:.1f}%.")
            profit_pct = ((current_mc_usd - buy_market_cap) / buy_market_cap) * 100
            return SellReason(
                category=SellCategory.TAKE_PROFIT,
                details=f"Take Profit Hit: Up {profit_pct:.1f}% from entry (${buy_market_cap:.0f} => ${current_mc_usd:.0f})"
            )

        return None
