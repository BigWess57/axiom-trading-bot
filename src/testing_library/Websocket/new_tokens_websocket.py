#!/usr/bin/env python3
"""
WebSocket Example - Monitor New Token Launches in Real-Time

This example demonstrates how to:
1. Connect to Axiom's WebSocket server
2. Subscribe to new token launches
3. Handle incoming token data in real-time
4. Automatically refresh tokens if the connection fails
5. Persist refreshed tokens to .env file

Features:
- Automatic token refresh on connection failure (up to 2 retries)
- Automatic token persistence to .env file after successful refresh
- Graceful error handling with helpful user guidance
- Real-time token data streaming

Requirements:
- Fresh authentication tokens in .env file (auth-access-token and auth-refresh-token)
- If automatic refresh fails, copy fresh tokens from browser:
  * Open axiom.trade in browser
  * F12 → Application/Storage → Cookies → https://axiom.trade
  * Copy auth-access-token and auth-refresh-token values to .env

Usage:
    PYTHONPATH=. python3 testing_library/Websocket/new_tokens_websocket.py
"""
import asyncio
from src.utils.connection_helpers import connect_with_retry

async def handle_new_tokens(tokens):
    """Handle incoming token data"""
    for token in tokens:
        print(f"🚨 NEW TOKEN: {token.get('token_name', 'Unknown')}")
        print(f"   Ticker: {token.get('token_ticker', 'N/A')}")
        print(f"   Address: {token.get('token_address', 'N/A')}")
        print(f"   Protocol: {token.get('protocol', 'N/A')}")
        print(f"   Initial Liquidity: {token.get('initial_liquidity_sol', 0):.2f} SOL")
        print()

async def main():
    """Main entry point for the new tokens WebSocket monitor"""
    # Define the subscription function
    async def do_subscribe(ws_client):
        return await ws_client.subscribe_new_tokens(
            callback=handle_new_tokens
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client = await connect_with_retry(do_subscribe)
    
    if success:
        print("✅ Connected and subscribed to new token launches!")
        # Start the message loop (blocks forever)
        await ws_client.ensure_connection_and_listen()
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")