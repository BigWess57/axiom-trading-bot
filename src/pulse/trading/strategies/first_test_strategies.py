"""
This is a simple example of a trading bot that trades based on ?? (first test)
"""
from typing import Callable, Optional, List, Tuple
from datetime import datetime, timezone
import logging
from src.pulse.types import PulseToken, SellReason, SellCategory, TradeTakenInformation, TradeResult, TokenState
from src.pulse.trading.strategies.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)

class FirstTestStrategy:
    """First test trading strategy"""
    
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
        """Evaluate if we should buy this token. Returns (should_buy, size_multiplier, confidence)"""
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

        confidence = self._calculate_confidence(state, sol_price)
        if confidence < self.config.confidence.min_confidence_score:
            return False, 0.0, 0.0

        if not self._check_for_buy_signal(token, past_trades_on_token, sol_price):
            return False, 0.0, 0.0

        size_multiplier = 0.5
        if confidence >= self.config.confidence.good_confidence_score:
            size_multiplier = 1.0

        logger.info(f"SHOULD BUY signal for {token.ticker} with confidence {confidence:.2f} (Size: {size_multiplier}x)")
        return True, size_multiplier, confidence
    
    def should_sell(self, trade_info: TradeTakenInformation) -> Optional[SellReason]:
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

        if (datetime.now(timezone.utc) - trade_info.time_bought).total_seconds() > self.config.risk.max_holding_time:
            hold_time_minutes = self.config.risk.max_holding_time / 60
            logger.info(f"Max holding time of {hold_time_minutes} minutes for {token.ticker} reached. Selling.")
            return SellReason(
                category=SellCategory.MAX_HOLD_TIME,
                details=f"Held for {hold_time_minutes:.1f} minutes"
            )
        
        return None
    

    ####### SECURITY #######
    def check_holder_safety(self, state: TokenState, holders: List[List[any]]):
        """
        Check if top holders have sufficient SOL balance.
        Updates state.holder_safety_score.
        """
        # Check Top 30 (indices 1 to 30, skipping LP at 0 if applicable per user usage)
        top_holders = holders[1:self.config.safety.holder_check_count + 1] # Slicing handles shorter lists gracefully
        total_checked = len(top_holders)
        
        if total_checked == 0:
                state.holder_safety_score = 0.2
                return

        low_balance_count = 0
        
        for h in top_holders:
            # h[2] is sol balance
            if len(h) > 2 and float(h[2]) < self.config.safety.min_holder_sol_balance:
                low_balance_count += 1
        
        # Calculate Score (Ratio of SAFE holders)
        safe_count = total_checked - low_balance_count
        score = safe_count / total_checked
        
        state.holder_safety_score = score
        
        is_safe = score >= self.config.confidence.holder_safety_threshold_low
        
        log_level = logging.DEBUG if is_safe else logging.INFO
        msg = (f"Holder Safety for {state.token.ticker}: Score {score:.2f} ({low_balance_count}/{total_checked} low balance)")
        logger.log(log_level, msg)

    def _security_checkup(self, token: PulseToken, sol_price: float) -> Optional[str]:
        """
        Perform security checkups.
        Returns None if all checks pass, or a string describing the failure reason.
        """
        
        # All these are now configurable
        if token.top10_holders_percent > self.config.safety.max_top10_percent:
            return f"Top 10 holders own {token.top10_holders_percent:.1f}% (max {self.config.safety.max_top10_percent}%)"
        if token.dev_holding_percent > self.config.safety.max_dev_holding_percent:
            return f"Dev holds {token.dev_holding_percent:.1f}% (max {self.config.safety.max_dev_holding_percent}%)"
        if token.insiders_percent > self.config.safety.max_insiders_percent:
            return f"Insiders hold {token.insiders_percent:.1f}% (max {self.config.safety.max_insiders_percent}%)"
        if token.bundled_percent > self.config.safety.max_bundled_percent:
            return f"Bundled {token.bundled_percent:.1f}% (max {self.config.safety.max_bundled_percent}%)"
        if token.holders == 0:
            return "No holders"
        if token.fees_paid == 0:
            return "No fees paid"
        if token.holders > 0 and token.pro_traders_count * 100 / token.holders < self.config.safety.min_pro_trader_percent:
            pro_trader_pct = (token.pro_traders_count * 100 / token.holders)
            return f"Only {pro_trader_pct:.1f}% pro traders (min {self.config.safety.min_pro_trader_percent}%)"
        if token.fees_paid > 0 and token.volume_total * sol_price / token.fees_paid > self.config.safety.max_volume_fees_ratio:
            ratio = token.volume_total * sol_price / token.fees_paid
            return f"Volume (in dollars)/fees(in SOL) ratio too high ({ratio:.0f}, max {self.config.safety.max_volume_fees_ratio})"
        
        return None  # All checks passed



    ####### STRATEGY #######
    def _check_for_buy_signal(self, token: PulseToken, past_trades_on_token: List[TradeResult], sol_price: float) -> bool:
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
        if token.volume_total < token.market_cap:
            return False
        
        return True

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


    def _calculate_confidence(self, state: TokenState, sol_price: float) -> float:
        """
        Calculate confidence score (0-100) based on snapshots & safety.
        Baseline: 50
        """
        if sol_price <= 0:
            return 0.0

        score = self.config.confidence.baseline_confidence_score
        token = state.token
        
        # 1. Holder Safety Impact
        # Score is 0.0 to 1.0 (Ratio of SAFE holders)
        # User Logic:
        # < 10 low balance (safe > 20/30 = 0.66) -> Good sign
        # < 20 low balance (safe > 10/30 = 0.33) -> Kind of safe
        # > 20 low balance (safe < 10/30 = 0.33) -> Fail
        
        if state.holder_safety_score is not None:
             hs = state.holder_safety_score
             
             if hs > self.config.confidence.holder_safety_threshold_high:
                 score += self.config.confidence.confidence_boost_high_holder_safety
             elif hs > self.config.confidence.holder_safety_threshold_low:
                 score += 0
             else:
                 score -= self.config.confidence.confidence_penalty_low_holder_safety
        
        # 2. ATH Impact
        if token.market_cap * sol_price < state.ath_market_cap * self.config.confidence.ath_impact_threshold:
            logger.debug(f"Token {token.ticker} is at {token.market_cap * sol_price} and ATH is {state.ath_market_cap}. Confidence penalty applied.")
            score -= self.config.confidence.confidence_penalty_ath_impact

        # 3. Value/Holder Trend (Lower MC/Holder ratio is better generally for distribution?)
        # User Logic: "If MC/holders is decreasing (meaning num holders compared to MC is increasing), good sign"
        lookback = min(self.config.confidence.distribution_trend_lookback, len(state.snapshots))
        if lookback > 0:
            # Current Ratio
            current_holders = token.holders if token.holders > 0 else 1
            current_ratio = (token.market_cap * sol_price) / current_holders
            
            # Avg Past Ratio (last N)
            past_ratios = []
            for s in state.snapshots[-lookback:]:
                h = s.holders if s.holders > 0 else 1
                r = s.market_cap / h
                past_ratios.append(r)
            
            if past_ratios:
                # Compare latest snapshot vs average of previous 4
                latest_ratio = past_ratios[-1]
                avg_prev_ratio = sum(past_ratios[:-1]) / len(past_ratios[:-1]) if len(past_ratios) > 1 else latest_ratio
                
                if current_ratio < avg_prev_ratio:
                    score += self.config.confidence.confidence_boost_improving_distribution_ratio
                else:
                    score -= self.config.confidence.confidence_penalty_worsening_distribution_ratio

        # 4. Activity (Txns)
        now = datetime.now(timezone.utc)
        old_time = now.timestamp() - self.config.confidence.activity_lookback_seconds
        
        # Find snapshot closest to 1 min ago
        old_snapshot = None
        for s in state.snapshots:
            if s.timestamp.timestamp() > old_time:
                break
            old_snapshot = s
            
        if old_snapshot:
            # Delta Txns
            new_txns = state.snapshots[-1].txns - old_snapshot.txns
            if new_txns > self.config.confidence.min_txns_for_boost:
                score += self.config.confidence.confidence_boost_high_activity
            
            # Delta Buys vs Sells
            new_buys = state.snapshots[-1].buys - old_snapshot.buys
            new_sells = state.snapshots[-1].sells - old_snapshot.sells
            
            if new_buys > new_sells:
                score += self.config.confidence.confidence_boost_buying_pressure
        
        return max(0.0, min(100.0, score))