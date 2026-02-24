from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

# ============= Pulse Token =============

class PulseToken(BaseModel):
    """Represents a token from the Pulse feed"""
    # Basic Identity
    pair_address: str
    token_address: str
    creator: str
    name: str
    ticker: str
    image: Optional[str] = None
    chain_id: int
    protocol: Optional[str] = None
    
    # Socials & Info
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    creator_name: Optional[str] = None
    
    # Holder Analysis
    top10_holders_percent: float = 0.0
    dev_holding_percent: float = 0.0
    snipers_percent: float = 0.0
    insiders_percent: float = 0.0
    bundled_percent: float = 0.0
    holders: int = 0
    
    # Financial Metrics
    volume_total: float = 0.0
    market_cap: float = 0.0
    fees_paid: float = 0.0
    total_supply: float = 0.0
    
    # Activity
    txns_total: int = 0
    buys_total: int = 0
    sells_total: int = 0
    pro_traders_count: int = 0
    
    # Timestamps
    migrated_at: Optional[str] = None
    created_at: Optional[str] = None
    
    # Dev Info
    dev_tokens_migrated: int = 0
    dev_tokens_created: int = 0
    
    # Social Metrics
    famous_kols: int = 0
    active_users_watching: int = 0
    twitter_followers: int = 0
    
    # Category tracking
    category: Optional[str] = None  # "newPairs", "finalStretch", or "migrated"
    
    # Debug: Raw field mapping
    raw_fields: Dict[int, Any] = Field(default_factory=dict)


# ============= Trading Strategy Types =============

class SellCategory(str, Enum):
    """Categories for sell reasons"""
    CATEGORY_CHANGE = "category_change"
    SECURITY_FAILED = "security_failed"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLD_TIME = "max_hold_time"
    TOKEN_REMOVED = "token_removed"


class SellReason(BaseModel):
    """Structured reason for selling a token"""
    category: SellCategory
    details: Optional[str] = None


# ============= Trading Information Types =============

class TradeInfo(BaseModel):
    """Represents an active trade (TradeTakenInformation + calculated stats)."""
    token: PulseToken
    # Core fields from TradeTakenInformation
    time_bought: str # datetime serialized to isoformat string usually for API
    
    # Calculated fields for Dashboard display
    entry_mc: float
    pnl_pct: float
    pnl_absolute: float


class TradeResult(BaseModel):
    """Result of a trade (completed)."""
    pair_address: str
    token_ticker: str
    token_name: str
    profit: float
    fees_paid: float
    sell_reason: Optional[SellReason] = None
    time_bought: str # datetime serialized to isoformat string
    time_sold: str # datetime serialized to isoformat string
    buy_market_cap: float
    sell_market_cap: float


# ============= States =============

class BotStats(BaseModel):
    """Represents the bot's statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_fees_paid: float
    runtime: float
    balance: float


class BotState(BaseModel):
    """Represents the bot's state."""
    stats: BotStats
    active_trades: List[TradeInfo]
    recent_trades: List[TradeResult]

