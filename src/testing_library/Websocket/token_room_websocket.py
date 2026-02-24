import asyncio
from axiomtradeapi import AxiomTradeClient
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (three levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

# Now we can import from src and load .env regardless of where we run the script from
from src.utils.connection_helpers import connect_with_retry
load_dotenv(PROJECT_ROOT / ".env")

# Cache for token info
token_info_cache = {}

async def get_token_supply(client, pair_address):
    """Fetch token supply for market cap calculation"""
    if pair_address in token_info_cache:
        return token_info_cache[pair_address]
    
    try:
        # You'd need to implement a method to get token info by pair address
        # For now, we'll use a placeholder or fetch from a new token list
        # This is a simplified approach - you may need to adjust based on available API methods
        token_info_cache[pair_address] = 1000000000  # Default estimate (1B tokens)
        return token_info_cache[pair_address]
    except:
        return 1000000000  # Default fallback

async def handle_new_tokens_info(info, client=None):
    """Handle incoming token data"""
    # Extract key information
    print(info)
    
async def main():
    # Initialize with authentication
    client = AxiomTradeClient(
        auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
        refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
    )
    
    print("🔍 Monitoring token price...")
    print("Press Ctrl+C to stop\n")
    
    # Ensure we have fresh tokens
    if not client.ensure_authenticated():
        print("❌ Failed to authenticate. Please check your tokens.")
        return
    
    token_info = client.get_token_info_detailed()
    print(f"✅ Authenticated. Token expires in {token_info.get('time_until_expiry', 'unknown')}")
    
    # Create callback wrapper with client reference
    async def info_callback(info):
        await handle_new_tokens_info(info, client)
    
    # Define the subscription function
    async def do_subscribe(ws_client):
        return await ws_client.subscribe_token_price(
            token="b-EJqdrv84g94X1eaE5f2Kznt6KyGehuRHg3KsyrCPJWS",
            callback=info_callback
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client = await connect_with_retry(client, do_subscribe)
    
    if success:
        print("✅ Connected and subscribed to token price updates!")
        # Start the message loop (blocks forever)
        await ws_client.start()
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")