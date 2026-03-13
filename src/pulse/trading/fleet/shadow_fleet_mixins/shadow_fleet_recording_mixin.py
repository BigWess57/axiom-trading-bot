import logging
from datetime import datetime, timezone
from src.pulse.types import PulseToken, SharedTokenState, TokenSnapshot

logger = logging.getLogger("ShadowFleetManager")

class ShadowFleetRecordingMixin:
    """Mixin for managing database logging and state snapshots."""

    def _record_snapshot(self, token: PulseToken, state: SharedTokenState):
        """Record a snapshot of token metrics (every ~2 seconds)"""
        now = datetime.now(timezone.utc)
        
        if state.last_snapshot_time:
            delta = (now - state.last_snapshot_time).total_seconds()
            if delta < 2.0:
                return

        state.last_snapshot_time = now
        
        # Create Snapshot
        snapshot = TokenSnapshot(
            timestamp=now,
            market_cap=token.market_cap * getattr(self, "current_sol_price", 0.0),
            txns=token.txns_total,
            buys=token.buys_total,
            sells=token.sells_total,
            holders=token.holders,
            kols=token.famous_kols,
            users_watching=token.active_users_watching
        )

        # Limit history (3 minutes @ 2s = 90 snapshots)
        if len(state.snapshots) > 100: # generous buffer
            state.snapshots.pop(0)

        state.snapshots.append(snapshot)
        logger.debug(f"Recorded snapshot for {token.ticker}: {snapshot}")

    def _record_db_snapshot(self, token: PulseToken, state: SharedTokenState):
        """Record a mutable snapshot to the SQLite database (every ~2 seconds)"""
        now = datetime.now(timezone.utc)
        
        if state.last_db_snapshot_time:
            delta = (now - state.last_db_snapshot_time).total_seconds()
            if delta < 2.0:
                return

        state.last_db_snapshot_time = now
        
        # Log to DB and save the returned primary key ID
        if hasattr(self, "recorder"):
            inserted_id = self.recorder.log_db_snapshot(token, now.isoformat())
            if inserted_id:
                state.latest_db_snapshot_id = inserted_id
