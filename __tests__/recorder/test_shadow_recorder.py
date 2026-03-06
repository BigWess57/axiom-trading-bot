import os
import sqlite3
import pytest
from datetime import datetime, timezone

from src.pulse.types import PulseToken
from src.pulse.trading.fleet.shadow_recorder import ShadowRecorder, ShadowTradeRecord

@pytest.fixture
def recorder(tmp_path):
    """Fixture to provide a fresh ShadowRecorder instance pointing to a temporary directory."""
    log_dir = str(tmp_path / "test_logs")
    r = ShadowRecorder(log_dir=log_dir)
    yield r
    # Connections are closed per method, so no explicit teardown needed, tmp_path cleans up itself.

@pytest.fixture
def sample_pulse_token():
    """Provides a dummy PulseToken for testing."""
    return PulseToken(
        pair_address="Pair123",
        token_address="TokenBase",
        creator="DevAlpha",
        name="Test Coin",
        ticker="TST",
        image="https://img.com/a",
        chain_id=101,
        protocol="Pump V1",
        website="https://test.com",
        twitter="@test",
        telegram="t.me/test",
        creator_name="Alpha",
        top10_holders_percent=15.5,
        dev_holding_percent=2.0,
        snipers_percent=1.5,
        insiders_percent=5.0,
        bundled_percent=3.0,
        holders=1250,
        volume_total=500000.0,
        market_cap=250000.0,
        fees_paid=200.0,
        bonding_curve_percentage=85.0,
        total_supply=1000000000.0,
        txns_total=850,
        buys_total=500,
        sells_total=350,
        pro_traders_count=12,
        migrated_at="2026-03-01T12:00:00Z",
        created_at="2026-03-01T10:00:00Z",
        dev_tokens_migrated=0,
        dev_tokens_created=10000,
        famous_kols=2,
        active_users_watching=45,
        twitter_followers=1200
    )


def test_database_initialization(recorder):
    """Verifies that all tables are created correctly upon initialization."""
    assert os.path.exists(recorder.filepath)
    
    with sqlite3.connect(recorder.filepath) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "tokens" in tables
        assert "token_snapshots" in tables
        assert "trades" in tables
        assert "market_weather" in tables


def test_log_token(recorder, sample_pulse_token):
    """Tests the insertion of an immutable token."""
    recorder.log_token(sample_pulse_token)
    
    with sqlite3.connect(recorder.filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tokens WHERE pair_address = ?", (sample_pulse_token.pair_address,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["name"] == "Test Coin"
        assert row["creator"] == "DevAlpha"
        assert row["total_supply"] == 1000000000.0

        # Attempt to log again to ensure INSERT OR IGNORE works without crashing
        recorder.log_token(sample_pulse_token)
        cursor.execute("SELECT COUNT(*) FROM tokens WHERE pair_address = ?", (sample_pulse_token.pair_address,))
        count = cursor.fetchone()[0]
        assert count == 1


def test_log_db_snapshot(recorder, sample_pulse_token):
    """Tests insertion of mutable snapshot and its returned auto-incrementing ID."""
    # Insert parent token first to satisfy Foreign Key rule (though SQLite FKs are OFF by default unless PRAGMA foreign_keys = ON)
    recorder.log_token(sample_pulse_token)
    
    now_iso = datetime.now(timezone.utc).isoformat()
    snapshot_id = recorder.log_db_snapshot(sample_pulse_token, now_iso)
    
    assert snapshot_id is not None
    assert isinstance(snapshot_id, int)
    
    with sqlite3.connect(recorder.filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM token_snapshots WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["pair_address"] == "Pair123"
        assert row["market_cap"] == 250000.0
        assert row["holders"] == 1250


def test_log_trade(recorder, sample_pulse_token):
    """Tests trade insertion and foreign key linkage to snapshot."""
    # 1. Setup Parent Data
    recorder.log_token(sample_pulse_token)
    snapshot_id = recorder.log_db_snapshot(sample_pulse_token, datetime.now(timezone.utc).isoformat())
    
    # 2. Setup Trade Record
    trade = ShadowTradeRecord(
        strategy_id="Bot_XGBoost_Prep",
        token_symbol="TST",
        token_address="TokenBase",
        entry_price=0.00025,
        exit_price=0.00030,
        pnl_percent=20.0,
        profit=5.0,
        fees_paid=0.1,
        duration_seconds=45.5,
        exit_reason="category_change",
        entry_confidence=0.88,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sell_snapshot_id=snapshot_id
    )
    
    # 3. Insert and Verify
    recorder.log_trade(trade)
    
    with sqlite3.connect(recorder.filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE strategy_id = ?", ("Bot_XGBoost_Prep",))
        row = cursor.fetchone()
        
        assert row is not None
        assert row["pnl_percent"] == 20.0
        assert row["sell_snapshot_id"] == snapshot_id


def test_log_market_weather(recorder):
    """Tests tracking the global market state."""
    weather_data = {
        "timestamp": "2026-03-06T19:00:00Z",
        "totalTransactions": 15000,
        "totalBuyTransactions": 8000,
        "totalSellTransactions": 7000,
        "totalMigrations": 5,
        "totalTokensCreated": 120,
        "totalTraders": 4500,
        "totalVolume": 250000.50,
        "totalBuyVolume": 130000.25,
        "totalSellVolume": 120000.25
    }
    
    recorder.log_market_weather(weather_data)
    
    with sqlite3.connect(recorder.filepath) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM market_weather")
        row = cursor.fetchone()
        
        assert row is not None
        assert row["totalTraders"] == 4500
        assert row["totalVolume"] == 250000.50
        assert row["totalSellTransactions"] == 7000
