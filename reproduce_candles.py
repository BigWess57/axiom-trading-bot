import asyncio
import os
from dotenv import load_dotenv
from axiomtradeapi import AxiomTradeClient
from datetime import datetime, timedelta, timezone

load_dotenv()

async def main():
    client = AxiomTradeClient(
        auth_token=os.getenv('AUTH_TOKEN'),
        refresh_token=os.getenv('REFRESH_TOKEN')
    )
    
    # 1. Test with an ESTABLISHED token (should have candles)
    pair_address = "2KkH82Sw8wMyXEc8NH8LRvqYd5kGp6276od6Q2pMYJB4" # Known pair
    print(f"\n--- Testing Established Token: {pair_address} ---")
    
    try:
        pair_info = client.get_pair_info(pair_address)
        last_tx = client.get_last_transaction(pair_address)
        
        def to_ms(val):
            if isinstance(val, int): return val
            if isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    return int(dt.timestamp() * 1000)
                except:
                    return None
            return None

        open_trading = to_ms(pair_info.get("openTrading"))
        pair_created_at = to_ms(pair_info.get("createdAt"))
        last_tx_time = to_ms(last_tx.get("createdAt"))
        v = last_tx_time or int(datetime.now(timezone.utc).timestamp() * 1000)
        
        # Ranges
        to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        from_ts = to_ts - (60 * 60 * 1000) # 1 hour
        
        print(f"Fetching 1m candles for last hour...")
        candles = client.get_pair_chart(
             pair_address=pair_address,
             from_ts=from_ts,
             to_ts=to_ts,
             open_trading=open_trading,
             pair_created_at=pair_created_at,
             last_transaction_time=last_tx_time,
             currency="USD",
             interval="1m",
             count_bars=300,
             v=v
        )
        
        if isinstance(candles, dict):
            data = candles.get('candles') or candles.get('bars') or []
            print(f"Candles Count: {len(data)}")
            if len(data) > 0:
                print(f"First Candle: {data[0]}")
        else:
             print(f"Response type: {type(candles)}")

    except Exception as e:
        print(f"Error testing established token: {e}")


    # 2. Test "New Token" Simulation (Short timeframe)
    # effectively asking for candles in a range that might not have closed bars
    print(f"\n--- Testing 'New Token' Simulation (Very short range) ---")
    
    to_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    from_ts = to_ts - (30 * 1000) # 30 seconds ago
    
    print(f"Fetching 1m candles for last 30 seconds (impossible to have 1m candle?)...")
    try:
         candles = client.get_pair_chart(
             pair_address=pair_address, # Same pair, but impossible range
             from_ts=from_ts,
             to_ts=to_ts,
             open_trading=open_trading,
             pair_created_at=pair_created_at,
             last_transaction_time=last_tx_time,
             currency="USD",
             interval="1s",
             count_bars=300,
             v=v
        )
         if isinstance(candles, dict):
            data = candles.get('candles') or candles.get('bars') or []
            print(f"Candles Count: {len(data)}")
         else:
             print(f"Response type: {type(candles)}")
             
    except Exception as e:
        print(f"Error testing new token sim: {e}")

if __name__ == "__main__":
    asyncio.run(main())
