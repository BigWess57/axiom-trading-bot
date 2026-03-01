from typing import List, Optional
import logging
from src.pulse.types import PulseToken, TokenState
from src.pulse.trading.strategies.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)

class SecurityMixin:
    """Mixin for strategy security checks"""
    
    config: StrategyConfig

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
