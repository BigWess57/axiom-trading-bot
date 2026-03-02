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
            hs_high = self.config.confidence.holder_safety_threshold_high
            hs_low = self.config.confidence.holder_safety_threshold_low
            
            if hs > hs_high:
                boost_ratio = (hs - hs_high) / (1.0 - hs_high) if hs_high < 1.0 else 0.0
                score += self.config.confidence.confidence_boost_high_holder_safety * boost_ratio
            elif hs < hs_low:
                penalty_ratio = (hs_low - hs) / hs_low if hs_low > 0.0 else 0.0
                score -= self.config.confidence.confidence_penalty_low_holder_safety * penalty_ratio
        
        # 2. Security Checkup Impact
        top10_thresh = self.config.confidence.top10_penalty_threshold
        top10_max = self.config.safety.max_top10_percent
        if token.top10_holders_percent > top10_thresh and top10_max > top10_thresh:
            max_penalty = self.config.confidence.confidence_penalty_high_top10
            ratio = min(1.0, (token.top10_holders_percent - top10_thresh) / (top10_max - top10_thresh))
            penalty = (max_penalty / 2) + (max_penalty / 2) * ratio
            logger.debug("Token %s top 10 holders own %.1f%% > %s%%. Linear penalty %.1f applied.", token.ticker, token.top10_holders_percent, top10_thresh, penalty)
            score -= penalty
            
        bundled_thresh = self.config.confidence.bundled_penalty_threshold
        bundled_max = self.config.safety.max_bundled_percent
        if token.bundled_percent > bundled_thresh and bundled_max > bundled_thresh:
            max_penalty = self.config.confidence.confidence_penalty_high_bundled
            ratio = min(1.0, (token.bundled_percent - bundled_thresh) / (bundled_max - bundled_thresh))
            penalty = (max_penalty / 2) + (max_penalty / 2) * ratio
            logger.debug("Token %s bundled percent %.1f%% > %s%%. Linear penalty %.1f applied.", token.ticker, token.bundled_percent, bundled_thresh, penalty)
            score -= penalty

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
                if len(past_ratios) > 1:
                    prev_ratios = past_ratios[:-1]
                    # Apply linear weighting so more recent snapshots matter more
                    weights = range(1, len(prev_ratios) + 1)
                    weighted_sum = sum(r * w for r, w in zip(prev_ratios, weights))
                    avg_prev_ratio = weighted_sum / sum(weights)
                else:
                    avg_prev_ratio = latest_ratio
                
                if current_ratio < avg_prev_ratio:
                    improvement = (avg_prev_ratio - current_ratio) / avg_prev_ratio
                    max_inc = self.config.confidence.max_distribution_ratio_inc
                    boost_ratio = min(1.0, improvement / max_inc) if max_inc > 0 else 0.0
                    score += self.config.confidence.confidence_boost_improving_distribution_ratio * boost_ratio

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
            min_txns = self.config.confidence.min_txns_for_boost
            if new_txns > min_txns:
                max_inc = self.config.confidence.max_txns_inc_for_full_boost
                denom = max(1.0, max_inc - min_txns)
                boost_ratio = min(1.0, (new_txns - min_txns) / denom)
                score += self.config.confidence.confidence_boost_high_activity * boost_ratio
            
            new_buys = state.token.buys_total - old_snapshot.buys
            new_sells = state.token.sells_total - old_snapshot.sells
            
            ratio = new_buys / max(1, new_sells)
            if ratio > 1.0:
                max_ratio_inc = self.config.confidence.max_buy_sell_ratio_inc_for_full_boost
                denom_ratio = max(0.1, max_ratio_inc - 1.0)
                boost_ratio = min(1.0, (ratio - 1.0) / denom_ratio)
                score += self.config.confidence.confidence_boost_buying_pressure * boost_ratio
            
            new_kols = state.token.famous_kols - old_snapshot.kols
            if new_kols > 0:
                score += self.config.confidence.confidence_boost_new_kol * min(new_kols, self.config.confidence.max_kols_inc_for_full_boost)

            # Smooth active users watching via moving average (+/- 15s window around target points)
            recent_snaps = [s.users_watching for s in state.snapshots if s.timestamp.timestamp() >= now.timestamp() - 15.0]
            current_users_vals = recent_snaps + [state.token.active_users_watching]
            current_users_ma = sum(current_users_vals) / len(current_users_vals)
            
            old_window_snaps = [s.users_watching for s in state.snapshots if abs(s.timestamp.timestamp() - old_time) <= 10.0]
            if old_window_snaps:
                old_users_ma = sum(old_window_snaps) / len(old_window_snaps)
            else:
                old_users_ma = old_snapshot.users_watching

            new_users = current_users_ma - old_users_ma
            min_users = self.config.confidence.min_users_watching_increase
            if new_users > min_users:
                max_users_inc = self.config.confidence.max_users_watching_inc_for_full_boost
                denom_users = max(1.0, max_users_inc - min_users)
                boost_ratio = min(1.0, (new_users - min_users) / denom_users)
                score += self.config.confidence.confidence_boost_users_watching * boost_ratio
        
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
