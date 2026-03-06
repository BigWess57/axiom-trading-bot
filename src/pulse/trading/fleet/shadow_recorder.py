import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Optional, Dict, Any

from src.pulse.types import PulseToken

logger = logging.getLogger("ShadowRecorder")

@dataclass
class ShadowTradeRecord:
    """
    Represents a single trade taken by a virtual bot.
    """
    strategy_id: str
    token_symbol: str
    token_address: str
    entry_price: float
    exit_price: float
    pnl_percent: float
    profit: float
    fees_paid: float
    duration_seconds: float
    exit_reason: str
    entry_confidence: float
    timestamp: str  # ISO format
    sell_snapshot_id: Optional[int] = None # FK to token_snapshots


class ShadowRecorder:
    """
    Logs shadow trades, token data, and market weather to a SQLite database.
    """
    def __init__(self, log_dir: str = "data/shadow_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a new DB file for this session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(log_dir, f"shadow_run_{timestamp}.db")
        
        # Lock for thread-safety (SQLite is safe with multiple threads using the same connection if careful, 
        # but since VirtualBots might hit this concurrently, a simple lock is safest)
        self._db_lock = Lock()
        
        self._initialize_db()

    def _get_connection(self):
        """Helper to get a DB connection with dict row factory"""
        # We create a new connection per operation or use one per thread. 
        # For simple concurrent appends, creating a throwaway connection 
        # inside the lock is the safest and easiest way to avoid "same thread" errors.
        conn = sqlite3.connect(self.filepath, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        """Create all necessary tables using rigorous normalized schema"""
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 1. Immutable Tokens
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS tokens (
                            pair_address TEXT PRIMARY KEY,
                            token_address TEXT,
                            creator TEXT,
                            name TEXT,
                            ticker TEXT,
                            protocol TEXT,
                            website TEXT,
                            twitter TEXT,
                            telegram TEXT,
                            creator_name TEXT,
                            total_supply REAL,
                            migrated_at TEXT,
                            created_at TEXT,
                            dev_tokens_migrated INTEGER,
                            dev_tokens_created INTEGER
                        )
                    ''')
                    
                    # 2. Mutable Token Snapshots
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS token_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            pair_address TEXT,
                            timestamp TEXT,
                            top10_holders_percent REAL,
                            dev_holding_percent REAL,
                            snipers_percent REAL,
                            insiders_percent REAL,
                            bundled_percent REAL,
                            holders INTEGER,
                            volume_total REAL,
                            market_cap REAL,
                            fees_paid REAL,
                            bonding_curve_percentage REAL,
                            txns_total INTEGER,
                            buys_total INTEGER,
                            sells_total INTEGER,
                            pro_traders_count INTEGER,
                            famous_kols INTEGER,
                            active_users_watching INTEGER,
                            twitter_followers INTEGER,
                            FOREIGN KEY(pair_address) REFERENCES tokens(pair_address)
                        )
                    ''')

                    # 3. Trades
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            strategy_id TEXT,
                            token_symbol TEXT,
                            token_address TEXT,
                            entry_price REAL,
                            exit_price REAL,
                            pnl_percent REAL,
                            profit REAL,
                            fees_paid REAL,
                            duration_seconds REAL,
                            exit_reason TEXT,
                            entry_confidence REAL,
                            timestamp TEXT,
                            sell_snapshot_id INTEGER,
                            FOREIGN KEY(sell_snapshot_id) REFERENCES token_snapshots(id)
                        )
                    ''')

                    # 4. Market Weather
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS market_weather (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            totalTransactions INTEGER,
                            totalBuyTransactions INTEGER,
                            totalSellTransactions INTEGER,
                            totalMigrations INTEGER,
                            totalTokensCreated INTEGER,
                            totalTraders INTEGER,
                            totalVolume REAL,
                            totalBuyVolume REAL,
                            totalSellVolume REAL
                        )
                    ''')
                    
                    conn.commit()
        except Exception as e:
            logger.critical(f"Failed to initialize SQLite DB at {self.filepath}: {e}")

    def log_token(self, token: PulseToken):
        """Insert immutable token metadata exactly once."""
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO tokens (
                            pair_address, token_address, creator, name, ticker, protocol, website, twitter, telegram,
                            creator_name, total_supply, migrated_at, created_at,
                            dev_tokens_migrated, dev_tokens_created
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        token.pair_address, token.token_address, token.creator, token.name, token.ticker, token.protocol, token.website, token.twitter, token.telegram,
                        token.creator_name, token.total_supply, token.migrated_at, token.created_at,
                        token.dev_tokens_migrated, token.dev_tokens_created
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to log immutable token {token.ticker}: {e}")

    def log_db_snapshot(self, token: PulseToken, timestamp_iso: str) -> Optional[int]:
        """
        Insert a mutable token snapshot.
        Returns the SQLite row ID of the snapshot so that VirtualBots can attach it to trades.
        """
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO token_snapshots (
                            pair_address, timestamp, top10_holders_percent, dev_holding_percent,
                            snipers_percent, insiders_percent, bundled_percent, holders,
                            volume_total, market_cap, fees_paid, bonding_curve_percentage,
                            txns_total, buys_total, sells_total, pro_traders_count,
                            famous_kols, active_users_watching, twitter_followers
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        token.pair_address, timestamp_iso, token.top10_holders_percent, token.dev_holding_percent,
                        token.snipers_percent, token.insiders_percent, token.bundled_percent, token.holders,
                        token.volume_total, token.market_cap, token.fees_paid, token.bonding_curve_percentage,
                        token.txns_total, token.buys_total, token.sells_total, token.pro_traders_count,
                        token.famous_kols, token.active_users_watching, token.twitter_followers
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to log DB snapshot for {token.ticker}: {e}")
            return None

    def log_trade(self, record: ShadowTradeRecord):
        """Append a trade record into the database"""
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO trades (
                            strategy_id, token_symbol, token_address, entry_price, exit_price,
                            pnl_percent, profit, fees_paid, duration_seconds, exit_reason,
                            entry_confidence, timestamp, sell_snapshot_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record.strategy_id, record.token_symbol, record.token_address,
                        record.entry_price, record.exit_price, record.pnl_percent, record.profit,
                        record.fees_paid, record.duration_seconds, record.exit_reason,
                        record.entry_confidence, record.timestamp, record.sell_snapshot_id
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to log shadow trade: {e}")

    def log_market_weather(self, weather_data: dict):
        """Log hourly market weather data from StealthApiClient"""
        try:
            with self._db_lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO market_weather (
                            timestamp, totalTransactions, totalBuyTransactions, totalSellTransactions, totalMigrations, totalTokensCreated,
                            totalTraders, totalVolume, totalBuyVolume, totalSellVolume
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        weather_data['timestamp'],
                        weather_data['totalTransactions'],
                        weather_data['totalBuyTransactions'],
                        weather_data['totalSellTransactions'],
                        weather_data['totalMigrations'],
                        weather_data['totalTokensCreated'],
                        weather_data['totalTraders'],
                        weather_data['totalVolume'],
                        weather_data['totalBuyVolume'],
                        weather_data['totalSellVolume']
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to log market weather: {e}")
