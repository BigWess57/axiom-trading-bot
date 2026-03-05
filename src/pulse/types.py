"""
Centralized type definitions for the Pulse trading system.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, NamedTuple
from datetime import datetime
from enum import Enum



# ============= Pulse Token =============

@dataclass
class PulseToken:
    """Represents a token from the Pulse feed"""
    # Basic Identity (indices 0-7)
    pair_address: str
    token_address: str
    creator: str
    name: str
    ticker: str
    image: Optional[str]
    chain_id: int
    protocol: Optional[str]
    
    # Socials & Info (indices 9-11, 46)
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    creator_name: Optional[str] = None
    
    # Holder Analysis (indices 13-17, 28)
    top10_holders_percent: float = 0.0
    dev_holding_percent: float = 0.0
    snipers_percent: float = 0.0
    insiders_percent: float = 0.0
    bundled_percent: float = 0.0
    holders: int = 0
    
    # Financial Metrics (indices 18-20, 27)
    volume_total: float = 0.0
    market_cap: float = 0.0
    fees_paid: float = 0.0
    bonding_curve_percentage: float = 0.0
    total_supply: float = 0.0
    
    # Activity (indices 23-25, 29)
    txns_total: int = 0
    buys_total: int = 0
    sells_total: int = 0
    pro_traders_count: int = 0
    
    # Timestamps (indices 30, 34)
    migrated_at: Optional[str] = None
    created_at: Optional[str] = None
    
    # Dev Info (indices 33, 41)
    dev_tokens_migrated: int = 0
    dev_tokens_created: int = 0
    
    # Social Metrics (indices 40, 45, 47)
    famous_kols: int = 0
    active_users_watching: int = 0
    twitter_followers: int = 0
    
    # Category tracking
    category: Optional[str] = None  # "newPairs", "finalStretch", or "migrated"
    
    # Debug: Raw field mapping for manual field identification
    raw_fields: Dict[int, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_array(cls, data: List[Any], index_map: Optional[Dict[int, str]] = None) -> 'PulseToken':
        """Create a PulseToken from the raw array data"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Helper functions for safe type conversion
            def get_float(idx, default=0.0):
                try:
                    return float(data[idx]) if idx < len(data) and data[idx] is not None else default
                except (ValueError, TypeError):
                    return default

            def get_int(idx, default=0):
                try:
                    return int(data[idx]) if idx < len(data) and data[idx] is not None else default
                except (ValueError, TypeError):
                    return default
            
            def get_str(idx, default=None):
                try:
                    return str(data[idx]) if idx < len(data) and data[idx] else default
                except (ValueError, TypeError):
                    return default

            # Basic Identity (0-7)
            pair_address = data[0]
            token_address = data[1]
            creator = data[2]
            name = data[3]
            ticker = data[4]
            image = data[5]
            chain_id = data[6]
            protocol = data[7]
            
            # Socials & Info (9-11, 46) - CORRECTED indices
            website = get_str(9)
            twitter = get_str(10)
            telegram = get_str(11)
            creator_name = get_str(46)
            
            # Holder Analysis (13-17, 28)
            top10_holders_percent = get_float(13)
            dev_holding_percent = get_float(14)
            snipers_percent = get_float(15)
            insiders_percent = get_float(16)
            bundled_percent = get_float(17)
            holders = get_int(28)
            
            # Financial Metrics (18-20, 27)
            volume_total = get_float(18)
            market_cap = get_float(19)
            fees_paid = get_float(20)
            total_supply = get_float(27)
            
            # Activity (23-25, 29)
            txns_total = get_int(23)
            buys_total = get_int(24)
            sells_total = get_int(25)
            pro_traders_count = get_int(29)
            
            # Timestamps (30, 34)
            t1 = get_str(30)
            t2 = get_str(34)
            
            if t1 and t2:
                if t1 < t2:
                    migrated_at = t1
                    created_at = t2
                else:
                    migrated_at = t2
                    created_at = t1
            else:
                # Fallback if comparison not possible
                migrated_at = t1
                created_at = t2
            
            # Dev Info (33, 41)
            dev_tokens_migrated = get_int(33)
            dev_tokens_created = get_int(41)
            
            # Social Metrics (40, 45, 47)
            famous_kols = get_int(40)
            active_users_watching = get_int(45)
            twitter_followers = get_int(47)
            
            # Store ALL raw fields for debugging
            raw_fields = {}
            for idx in range(len(data)):
                raw_fields[idx] = data[idx]
            
            return cls(
                pair_address=pair_address,
                token_address=token_address,
                creator=creator,
                name=name,
                ticker=ticker,
                image=image,
                chain_id=chain_id,
                protocol=protocol,
                website=website,
                twitter=twitter,
                telegram=telegram,
                creator_name=creator_name,
                top10_holders_percent=top10_holders_percent,
                dev_holding_percent=dev_holding_percent,
                snipers_percent=snipers_percent,
                insiders_percent=insiders_percent,
                bundled_percent=bundled_percent,
                holders=holders,
                volume_total=volume_total,
                market_cap=market_cap,
                fees_paid=fees_paid,
                total_supply=total_supply,
                txns_total=txns_total,
                buys_total=buys_total,
                sells_total=sells_total,
                pro_traders_count=pro_traders_count,
                migrated_at=migrated_at,
                created_at=created_at,
                dev_tokens_migrated=dev_tokens_migrated,
                dev_tokens_created=dev_tokens_created,
                famous_kols=famous_kols,
                active_users_watching=active_users_watching,
                twitter_followers=twitter_followers,
                raw_fields=raw_fields
            )
        except Exception as e:
            logger.error(f"Error parsing token data: {e}")
            # Return a shell token if parsing fails
            return cls(
                pair_address=data[0] if len(data) > 0 else "unknown",
                token_address=data[1] if len(data) > 1 else "unknown",
                creator="unknown",
                name="Parse Error",
                ticker="ERR",
                image=None,
                chain_id=0,
                protocol="unknown"
            )


# ============= Trading Strategy Types =============

class SellCategory(Enum):
    """Categories for sell reasons"""
    CATEGORY_CHANGE = "category_change"
    SECURITY_FAILED = "security_failed"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLD_TIME = "max_hold_time"
    LOW_CONFIDENCE = "low_confidence"
    TOKEN_REMOVED = "token_removed"
    SHUTDOWN = "shutdown"


@dataclass
class SellReason:
    """Structured reason for selling a token"""
    category: SellCategory
    details: Optional[str] = None


# ============= Trading Information Types =============

@dataclass
class TradeTakenInformation:
    """Information about a trade taken"""
    token_bought_snapshot: PulseToken  # frozen at buy time — for logs/CSV only, never mutated
    buy_market_cap: float
    time_bought: datetime
    current_market_cap: float = 0.0  # updated each tick — used for SL/TP and sell pricing
    current_curve_pct: float = 0.0 # updated each tick - used for curve graduation exit
    peak_market_cap: float = 0.0 # highest market cap reached while holding
    highest_trailing_sl_mc: float = 0.0 # highest locked-in trailing stop loss
    fixed_take_profit_pct: Optional[float] = None # locked in if entered late
    fixed_stop_loss_pct: Optional[float] = None # locked in if entered late
    position_size: float = 0.0
    confidence: float = 0.0

class TradeResult(NamedTuple):
    """Result of a trade"""
    pair_address: str
    token_ticker: str
    token_name: str
    profit: float
    fees_paid: float
    sell_reason: SellReason
    time_bought: datetime
    time_sold: datetime
    buy_market_cap: float = 0.0
    sell_market_cap: float = 0.0
    position_size: float = 0.0


@dataclass
class TokenSnapshot:
    """Snapshot of token metrics at a point in time"""
    timestamp: datetime
    market_cap: float
    txns: int
    buys: int
    sells: int
    holders: int
    kols: int = 0
    users_watching: int = 0


@dataclass
class TokenState:
    """State of a token in the bot context"""
    token: PulseToken
    active_trade: Optional[TradeTakenInformation] = None
    past_trades: List[TradeResult] = field(default_factory=list)
    ath_market_cap: float = 0.0
    
    # Snapshot / Trend Data
    snapshots: List[TokenSnapshot] = field(default_factory=list)
    last_snapshot_time: Optional[datetime] = None
    
    # Security / Confidence
    holder_safety_score: Optional[float] = None # 0.0 to 1.0 (1.0 = All top holders have funds)

    @property
    def trade_count(self) -> int:
        return len(self.past_trades)


@dataclass
class BotGlobalState:
    """Global state across all trades for a virtual bot"""
    current_balance: float
    total_pnl: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    max_allowed_drawdown: float = 0.0


@dataclass
class SharedTokenState:
    """
    Shared Objective Reality for the Fleet.
    Managed by ShadowFleetManager. Read-only for VirtualBots.
    """
    token: PulseToken
    ath_market_cap: float = 0.0
    snapshots: List[TokenSnapshot] = field(default_factory=list)
    last_snapshot_time: Optional[datetime] = None
    
    # Raw Holder Data (List of [address, percentage, balance, ...])
    # fetched once by Manager
    raw_holders: Optional[List[List[Any]]] = None
    
    # Coordination flag for startup sync
    init_event: asyncio.Event = field(default_factory=asyncio.Event)
    is_fetching_data: bool = False