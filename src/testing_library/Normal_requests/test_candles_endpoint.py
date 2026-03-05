from axiomtradeapi import AxiomTradeClient
import os
from dotenv import load_dotenv
from datetime import datetime
from dateutil import parser as date_parser

# Load environment variables
load_dotenv()

# Initialize the client
client = AxiomTradeClient(
    auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
    refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
)

try:
    print(f"📊 Pair Chart Analysis")
    print(f"=" * 50)
    
    # Use a known pair address
    pair_address = "HTKaWC1MT5NGwcY38UmZjycings3UD5zrZ8AFnHEaRtn"
    print(f"Pair Address: {pair_address}")

    # 1. Get metadata needed for chart request
    print("Fetching metadata...")
    pair_info = client.get_pair_info(pair_address)
    tx_data = client.get_last_transaction(pair_address)
    
    def to_ms(val):
        if isinstance(val, int): return val
        if isinstance(val, str):
            try:
                # Parse ISO string
                dt = date_parser.parse(val)
                return int(dt.timestamp() * 1000)
            except:
                return None
        return None

    open_trading_raw = pair_info.get("openTrading")
    pair_created_at_raw = pair_info.get("createdAt")
    last_tx_time_raw = tx_data.get("createdAt")
    
    open_trading = to_ms(open_trading_raw)
    pair_created_at = to_ms(pair_created_at_raw)
    last_tx_time = to_ms(last_tx_time_raw)

    print(f"Metadata obtained successfully")

    # v: Use 'v' from tx_data or current time
    v = tx_data.get("v") or int(datetime.now().timestamp() * 1000)

    # 2. Calculate timestamps for 'from' and 'to' (30 mins)
    to_ts = int(datetime.now().timestamp() * 1000)
    from_ts = to_ts - (30 * 60 * 1000) # 30 minutes
    
    # 3. Fetch candles
    print(f"Fetching candles from {from_ts} to {to_ts}...")
    candles = client.get_pair_chart(
        pair_address=pair_address,
        from_ts=from_ts,
        to_ts=to_ts,
        open_trading=open_trading,
        pair_created_at=pair_created_at,
        last_transaction_time=last_tx_time,
        currency="USD",
        interval="1s",
        count_bars=2000,
        v=v
    )
    
    print(f"✅ Success!")
    
    # Check structure (candles list is usually under a key like 'bars' or 'candles' or just the list?)
    # Based on client implementation it returns response.json()
    # Let's inspect keywords
    keys = list(candles.keys()) if isinstance(candles, dict) else "List"
    print(f"Response Keys: {keys}")
    
    if isinstance(candles, dict) and ('candles' in candles or 'bars' in candles):
        data_list = candles.get('candles') or candles.get('bars')
        print(f"Count: {len(data_list)}")
        if len(data_list) > 0:
            print(f"Sample: {data_list[0]}")
    elif isinstance(candles, list):
         print(f"Count: {len(candles)}")
         if len(candles) > 0:
            print(f"Sample: {candles[0]}")

except Exception as e:
    raise Exception(f"❌ Error: {e}")
