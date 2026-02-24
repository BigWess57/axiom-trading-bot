from pydantic import BaseModel
from typing import List, Dict, Any

class TradeInfo(BaseModel):
    token_ticker: str
    token_name: str
    entry_mc: float
    current_mc: float
    pnl_pct: float
    pnl_absolute: float
    age_seconds: int
    pair_address: str

class BotStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    runtime: float
    balance: float

class BotState(BaseModel):
    stats: BotStats
    active_trades: List[TradeInfo]
    recent_trades: List[Dict[str, Any]]

# Simulating data from bot
data = {
    "stats": {
        "total_trades": 5,
        "winning_trades": 2,
        "losing_trades": 3,
        "win_rate": 40.0,
        "total_profit": -0.5,
        "runtime": 120.5,
        "balance": 9.5
    },
    "active_trades": [
        {
            "token_ticker": "TEST",
            "token_name": "Test Token",
            "entry_mc": 10000.0,
            "current_mc": 12000.0,
            "pnl_pct": 20.0,
            "pnl_absolute": 0.1,
            "age_seconds": 60,
            "pair_address": "0x123..."
        }
    ],
    "recent_trades": [
        {
            "pair_address": "0xabc...",
            "profit": 0.05,
            "time_sold": "2023-10-27T10:00:00"
        }
    ]
}

try:
    model = BotState(**data)
    print("Validation Successful")
    print(model.model_dump())
except Exception as e:
    print(f"Validation Failed: {e}")
