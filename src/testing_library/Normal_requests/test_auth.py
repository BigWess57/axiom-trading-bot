import os
from dotenv import load_dotenv
import time
import asyncio
from axiomtradeapi import AxiomTradeClient

# Load environment variables
load_dotenv()


async def test_authentication():
    """Test if authentication is working"""
    
    # Initialize client
    client = AxiomTradeClient(
        auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
        refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
    )
    if client.auth_manager.ensure_valid_authentication():
        print("✅ Authenticated and token is valid")
    else:
        raise Exception("❌ Authentication failed")
    # print("🔐 Testing authentication...")
    
    # # Test WebSocket connection (requires auth)
    # async def handle_tokens(tokens):
    #     print(f"✅ Authentication successful!")
    #     print(f"📡 Received {len(tokens)} tokens")
    #     return True  # Stop after first batch
    
    # try:
    #     await asyncio.wait_for(
    #         client.subscribe_new_tokens(callback=handle_tokens),
    #         timeout=10.0
    #     )
    # except asyncio.TimeoutError:
    #     print("⏱️ Test completed (timeout)")
    # except Exception as e:
    #     print(f"❌ Authentication failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_authentication())
