#!/usr/bin/env python3
"""
Test script to demonstrate the improved error messaging
"""
import asyncio
import os
from dotenv import load_dotenv
from axiomtradeapi import AxiomTradeClient

load_dotenv()

async def test():
    client = AxiomTradeClient(
        auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
        refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
    )
    
    # Test REST API (should work with refresh)
    print("Testing REST API...")
    if client.ensure_authenticated():
        balance = client.get_sol_balance("3xJbAVun5TubvK43w8HYP29kapfXxJGg8HEsRBT7B7XA")
        print(f"✅ REST API works: Balance = {balance} SOL")
    else:
        print("❌ REST API failed")
    
    print("\nTesting WebSocket...")
    ws_client = client.get_websocket_client()
    success = await ws_client.connect()
    
    if success:
        print("✅ WebSocket connected successfully!")
    else:
        print("❌ WebSocket connection failed - see error messages above")

if __name__ == "__main__":
    asyncio.run(test())
