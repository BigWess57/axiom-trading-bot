"""
Pulse WebSocket Filter Configuration

Define filter criteria for the three Pulse categories:
- newPairs: Newly launched tokens
- finalStretch: Tokens approaching bonding curve completion
- migrated: Tokens that have migrated to Raydium/other DEXs
"""

# Default filters for Pulse subscription
DEFAULT_PULSE_FILTERS = {
    "newPairs": {
        "age": {"max": 1, "min": 2, "unit": "minutes"},
        "atLeastOneSocial": False,
        "bondingCurve": {"max": None, "min": None},
        "botUsers": {"max": None, "min": None},
        "bundle": {"max": None, "min": None},
        "devHolding": {"max": 20, "min": None},
        "dexPaid": False,
        "excludeKeywords": [],
        "holders": {"max": None, "min": 1},
        "insiders": {"max": 30, "min": None},
        "liquidity": {"max": None, "min": None},
        "marketCap": {"max": 20000, "min": None},
        "mustEndInPump": False,
        "numBuys": {"max": None, "min": None},
        "numSells": {"max": None, "min": None},
        "protocols": {
            "bags": True,
            "bonk": True,
            "boop": True,
            "pump": True,
            "pumpAmm": False,
            "raydium": False,
            "moonshot": False
        },
        "searchKeywords": [],
        "snipers": {"max": None, "min": None},
        "telegram": False,
        "top10Holders": {"max": None, "min": None},
        "twitter": {"max": None, "min": None},
        "twitterExists": False,
        "twitterHandles": [],
        "txns": {"max": None, "min": None},
        "volume": {"max": None, "min": 200},
        "website": False
    },
    "finalStretch": {
        "age": {"max": 20, "min": None, "unit": "minutes"},
        "atLeastOneSocial": False,
        "bondingCurve": {"max": None, "min": None},
        "botUsers": {"max": None, "min": None},
        "bundle": {"max": None, "min": None},
        "devHolding": {"max": None, "min": None},
        "dexPaid": False,
        "excludeKeywords": [],
        "holders": {"max": None, "min": None},
        "insiders": {"max": None, "min": None},
        "liquidity": {"max": None, "min": None},
        "marketCap": {"max": None, "min": 6000},
        "mustEndInPump": False,
        "numBuys": {"max": None, "min": None},
        "numSells": {"max": None, "min": None},
        "protocols": {
            "bags": True,
            "bonk": True,
            "boop": True,
            "pump": True,
            "pumpAmm": False,
            "raydium": False,
            "moonshot": False
        },
        "searchKeywords": [],
        "snipers": {"max": None, "min": None},
        "telegram": False,
        "top10Holders": {"max": None, "min": None},
        "twitter": {"max": None, "min": None},
        "twitterExists": False,
        "twitterHandles": [],
        "txns": {"max": None, "min": None},
        "volume": {"max": None, "min": 4000},
        "website": False
    },
    "migrated": {
        "age": {"max": 60, "min": 65, "unit": "minutes"},
        "atLeastOneSocial": False,
        "bondingCurve": {"max": None, "min": None},
        "botUsers": {"max": None, "min": None},
        "bundle": {"max": None, "min": None},
        "devHolding": {"max": 20, "min": None},
        "dexPaid": False,
        "excludeKeywords": [],
        "fees": {"max": None, "min": 5},
        "holders": {"max": None, "min": None},
        "insiders": {"max": None, "min": None},
        "liquidity": {"max": None, "min": None},
        "marketCap": {"max": None, "min": 30000},
        "mustEndInPump": False,
        "numBuys": {"max": None, "min": None},
        "numMigrations": {"max": None, "min": None},
        "numSells": {"max": None, "min": None},
        "protocols": {
            "bags": True,
            "bonk": True,
            "boop": True,
            "pump": True,
            "pumpAmm": False,
            "raydium": False,
            "moonshot": False
        },
        "searchKeywords": [],
        "snipers": {"max": None, "min": None},
        "telegram": False,
        "top10Holders": {"max": None, "min": None},
        "twitter": {"max": None, "min": None},
        "twitterExists": False,
        "twitterHandles": [],
        "txns": {"max": None, "min": None},
        "volume": {"max": None, "min": None},
        "website": False
    }
}

# Aggressive filters - catch more tokens (looser criteria)
AGGRESSIVE_PULSE_FILTERS = {
    "newPairs": {
        **DEFAULT_PULSE_FILTERS["newPairs"],
        "age": {"max": 5, "min": None},  # Older tokens allowed
        "marketCap": {"max": 50000, "min": None},  # Higher market cap
        "devHolding": {"max": 30, "min": None},  # Higher dev holding allowed
    },
    "finalStretch": {
        **DEFAULT_PULSE_FILTERS["finalStretch"],
        "marketCap": {"max": None, "min": 5000},  # Lower min market cap
        "volume": {"max": None, "min": 2000},  # Lower volume requirement
    },
    "migrated": {
        **DEFAULT_PULSE_FILTERS["migrated"],
        "marketCap": {"max": None, "min": 20000},  # Lower min market cap
        "fees": {"max": None, "min": 1},  # Lower fee requirement
    }
}

# Conservative filters - only high-quality tokens (stricter criteria)
CONSERVATIVE_PULSE_FILTERS = {
    "newPairs": {
        **DEFAULT_PULSE_FILTERS["newPairs"],
        "age": {"max": 2, "min": None},  # Newer only
        "marketCap": {"max": 10000, "min": None},  # Lower market cap
        "devHolding": {"max": 10, "min": None},  # Lower dev holding
        "volume": {"max": None, "min": 500},  # Higher volume requirement
    },
    "finalStretch": {
        **DEFAULT_PULSE_FILTERS["finalStretch"],
        "marketCap": {"max": None, "min": 15000},  # Higher min market cap
        "volume": {"max": None, "min": 10000},  # Higher volume
        "devHolding": {"max": 20, "min": None},  # Stricter dev holding
    },
    "migrated": {
        **DEFAULT_PULSE_FILTERS["migrated"],
        "marketCap": {"max": None, "min": 50000},  # Higher min market cap
        "fees": {"max": None, "min": 5},  # Higher fees (more established)
        "devHolding": {"max": 15, "min": None},  # Stricter dev holding
    }
}
