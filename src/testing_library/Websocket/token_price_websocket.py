"""
Test Token Price WebSocket Subscription
Verifies that subscribe_token_price connects to a tokenand handles token price updates.
"""
import asyncio
from src.utils.connection_helpers import connect_with_retry

# Cache for token info
token_info_cache = {}

async def get_token_supply(pair_address):
    """Fetch token supply for market cap calculation"""
    if pair_address in token_info_cache:
        return token_info_cache[pair_address]
    
    try:
        # You'd need to implement a method to get token info by pair address
        # For now, we'll use a placeholder or fetch from a new token list
        # This is a simplified approach - you may need to adjust based on available API methods
        token_info_cache[pair_address] = 1000000000  # Default estimate (1B tokens)
        return token_info_cache[pair_address]
    except Exception as e:
        print(f"❌ Error fetching token supply: {e}")
        return 1000000000  # Default fallback

async def handle_new_tokens_prices(price):
    """Handle incoming token price data"""
    # Extract key information
    tx_type = price.get('type', 'unknown').upper()
    price_usd = price.get('price_usd', 0)
    token_amount = price.get('token_amount', 0)
    total_usd = price.get('total_usd', 0)
    liquidity_sol = price.get('liquidity_sol', 0)
    liquidity_token = price.get('liquidity_token', 0)
    is_new_holder = price.get('isNewHolder', False)
    is_pro_user = price.get('isProUser', False)
    # pair_address = price.get('pair_address', '')
    
    # Get token supply for market cap calculation
    # if client:
    #     supply = await get_token_supply(client, pair_address)
    # else:
    supply = 1000000000  # Default estimate
    
    # Calculate market cap: price * total supply
    market_cap_usd = price_usd * supply
    
    # Format output
    emoji = "🟢" if tx_type == "BUY" else "🔴"
    holder_flag = " 🆕" if is_new_holder else ""
    pro_flag = " 💎" if is_pro_user else ""
    
    # print(price)
    print(f"{emoji} {tx_type}{holder_flag}{pro_flag}")
    print(f"   Price: ${price_usd:.8f}")
    print(f"   Market Cap: ${market_cap_usd:,.2f}")
    print(f"   Amount: {token_amount:,.2f} tokens (${total_usd:.2f})")
    print(f"   Liquidity: {liquidity_sol:.2f} SOL / {liquidity_token:,.0f} tokens")
    print()

async def main():
    """Main entry point for the token price WebSocket monitor"""
    # Create callback wrapper with client reference
    async def price_callback(price):
        await handle_new_tokens_prices(price)
    
    # Define the subscription function
    async def do_subscribe(ws_client):
        return await ws_client.subscribe_token_price(
            token="59fwatH2hKcpxfwihntrrheR3G3LKzs6sNGs2qXYybor",
            callback=price_callback
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client, _ = await connect_with_retry(do_subscribe)
    
    if success:
        print("✅ Connected and subscribed to token price updates!")
        # Start the message loop (blocks forever)
        await ws_client.ensure_connection_and_listen()
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")