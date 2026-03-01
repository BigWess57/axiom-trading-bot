from datetime import datetime, timezone
import logging
from src.pulse.types import TokenState
from src.pulse.trading.strategies.strategy_models import StrategyConfig

logger = logging.getLogger(__name__)

class ConfidenceMixin:
    """Mixin for strategy confidence calculations"""
    
    config: StrategyConfig

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
            
            # Avg Past Ratio (last N, up to 10 sampled evenly)
            window_snapshots = state.snapshots[-lookback:]
            n_snapshots = len(window_snapshots)
            
            if n_snapshots > 10:
                # Sample exactly 10 evenly spaced indices, including first and last
                indices = [int(i * (n_snapshots - 1) / 9) for i in range(10)]
                sampled_snapshots = [window_snapshots[i] for i in indices]
            else:
                sampled_snapshots = window_snapshots

            past_ratios = []
            for s in sampled_snapshots:
                h = s.holders if s.holders > 0 else 1
                r = s.market_cap / h
                past_ratios.append(r)
            
            if past_ratios:
                # Compare latest snapshot vs average of previous 4
                latest_ratio = past_ratios[-1]
                avg_prev_ratio = sum(past_ratios[:-1]) / len(past_ratios[:-1]) if len(past_ratios) > 1 else latest_ratio
                
                if current_ratio < avg_prev_ratio:
                    score += self.config.confidence.confidence_boost_improving_distribution_ratio
                # else:
                #     score -= self.config.confidence.confidence_penalty_worsening_distribution_ratio

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
            new_txns = state.token.txns_total - old_snapshot.txns
            if new_txns > self.config.confidence.min_txns_for_boost:
                score += self.config.confidence.confidence_boost_high_activity
            
            # Delta Buys vs Sells
            new_buys = state.token.buys_total - old_snapshot.buys
            new_sells = state.token.sells_total - old_snapshot.sells
            
            if new_buys > new_sells:
                score += self.config.confidence.confidence_boost_buying_pressure
            
            # KOLs momentum
            new_kols = state.token.famous_kols - old_snapshot.kols
            if new_kols > 0:
                score += self.config.confidence.confidence_boost_new_kol * new_kols

            # Users watching momentum
            new_users = state.token.active_users_watching - old_snapshot.users_watching
            if new_users > self.config.confidence.min_users_watching_increase:
                score += self.config.confidence.confidence_boost_users_watching
        
        return max(0.0, min(100.0, score))
