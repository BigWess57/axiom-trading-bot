from enum import Enum

class WebSocketMode(Enum):
    """WebSocket connection modes"""
    NEW_PAIRS = "new_pairs"
    TOKEN_PRICE = "token_price"
    PULSE = "pulse"
    SOL_PRICE = "sol_price"
