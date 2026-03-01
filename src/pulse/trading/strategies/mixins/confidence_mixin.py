from datetime import datetime, timezone
import logging
from src.pulse.types import TokenState
from src.pulse.trading.strategies.strategy_models import StrategyConfig

logger = logging.getLogger(__name__)

class SecurityConfidenceMixin:
    """Mixin for calculating security-related confidence adjustments."""
    config: StrategyConfig

    def _apply_security_confidence(self, score: float, state: TokenState) -> float:
        token = state.token
        # 1. Holder Safety Impact
        if state.holder_safety_score is not None:
            hs = state.holder_safety_score
            
            if hs > self.config.confidence.holder_safety_threshold_high:
                score += self.config.confidence.confidence_boost_high_holder_safety
            elif hs > self.config.confidence.holder_safety_threshold_low:
                # Do nothing in between
                pass
            else:
                score -= self.config.confidence.confidence_penalty_low_holder_safety
        
        # 2. Security Checkup Impact
        if token.top10_holders_percent > self.config.confidence.top10_penalty_threshold:
            logger.debug("Token %s top 10 holders own %.1f%% > %s%%. Confidence penalty applied.", token.ticker, token.top10_holders_percent, self.config.confidence.top10_penalty_threshold)
            score -= self.config.confidence.confidence_penalty_high_top10
            
        if token.bundled_percent > self.config.confidence.bundled_penalty_threshold:
            logger.debug("Token %s bundled percent %.1f%% > %s%%. Confidence penalty applied.", token.ticker, token.bundled_percent, self.config.confidence.bundled_penalty_threshold)
            score -= self.config.confidence.confidence_penalty_high_bundled

        return score


class ChartHealthConfidenceMixin:
    """Mixin for calculating chart health-related confidence adjustments."""
    config: StrategyConfig

    def _apply_chart_health_confidence(self, score: float, state: TokenState, sol_price: float) -> float:
        token = state.token
        # 3. ATH Impact
        if token.market_cap * sol_price < state.ath_market_cap * self.config.confidence.ath_impact_threshold:
            logger.debug("Token %s is at %f and ATH is %f. Confidence penalty applied.", token.ticker, token.market_cap * sol_price, state.ath_market_cap)
            score -= self.config.confidence.confidence_penalty_ath_impact

        # 4. Value/Holder Trend (Lower MC/Holder ratio is better generally for distribution?)
        lookback = min(self.config.confidence.distribution_trend_lookback, len(state.snapshots))
        if lookback > 0:
            current_holders = token.holders if token.holders > 0 else 1
            current_ratio = (token.market_cap * sol_price) / current_holders
            
            window_snapshots = state.snapshots[-lookback:]
            n_snapshots = len(window_snapshots)
            
            if n_snapshots > 10:
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
                latest_ratio = past_ratios[-1]
                avg_prev_ratio = sum(past_ratios[:-1]) / len(past_ratios[:-1]) if len(past_ratios) > 1 else latest_ratio
                
                if current_ratio < avg_prev_ratio:
                    score += self.config.confidence.confidence_boost_improving_distribution_ratio

        return score


class ActivityConfidenceMixin:
    """Mixin for calculating activity-related confidence adjustments."""
    config: StrategyConfig

    def _apply_activity_confidence(self, score: float, state: TokenState) -> float:
        # 5. Activity (Txns)
        now = datetime.now(timezone.utc)
        old_time = now.timestamp() - self.config.confidence.activity_lookback_seconds
        
        old_snapshot = None
        for s in state.snapshots:
            if s.timestamp.timestamp() > old_time:
                break
            old_snapshot = s
            
        if old_snapshot:
            new_txns = state.token.txns_total - old_snapshot.txns
            if new_txns > self.config.confidence.min_txns_for_boost:
                score += self.config.confidence.confidence_boost_high_activity
            
            new_buys = state.token.buys_total - old_snapshot.buys
            new_sells = state.token.sells_total - old_snapshot.sells
            
            if new_buys > new_sells:
                score += self.config.confidence.confidence_boost_buying_pressure
            
            new_kols = state.token.famous_kols - old_snapshot.kols
            if new_kols > 0:
                score += self.config.confidence.confidence_boost_new_kol * new_kols

            new_users = state.token.active_users_watching - old_snapshot.users_watching
            if new_users > self.config.confidence.min_users_watching_increase:
                score += self.config.confidence.confidence_boost_users_watching
        
        return score


class ConfidenceMixin(SecurityConfidenceMixin, ChartHealthConfidenceMixin, ActivityConfidenceMixin):
    """Main Mixin for strategy confidence calculations, combining sub-mixins."""
    
    config: StrategyConfig

    def _calculate_confidence(self, state: TokenState, sol_price: float) -> float:
        """
        Calculate confidence score (0-100) based on snapshots & safety.
        Baseline: 50
        """
        if sol_price <= 0:
            return 0.0

        score = self.config.confidence.baseline_confidence_score
        
        score = self._apply_security_confidence(score, state)
        score = self._apply_chart_health_confidence(score, state, sol_price)
        score = self._apply_activity_confidence(score, state)
        
        return max(0.0, min(100.0, score))
