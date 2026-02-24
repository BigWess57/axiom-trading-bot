#!/usr/bin/env python3
"""
WebSocket Example - Monitor Sol Price in Real-Time

Usage:
    PYTHONPATH=. python3 testing_library/Websocket/sol_price_websocket.py
"""
import asyncio
from src.utils.connection_helpers import connect_with_retry

async def print_sol_price(sol_price):
    """Handle incoming token data"""
    print(f"🚨 SOL Price: {sol_price} SOL")
    print()

async def main():
    """Main entry point for the new tokens WebSocket monitor"""
    # Define the subscription function
    async def do_subscribe(ws_client):
        return await ws_client.subscribe_sol_price(
            callback=print_sol_price
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client = await connect_with_retry(do_subscribe)
    
    if success:
        print("✅ Connected and subscribed to SOL price!")
        # Start the message loop (blocks forever)
        await ws_client.ensure_connection_and_listen()
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")