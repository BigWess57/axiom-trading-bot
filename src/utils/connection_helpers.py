"""
WebSocket Helper Utilities

Provides common functionality for WebSocket connections:
- Automatic token refresh and retry logic
- Token persistence to .env file
- Clean connection handling
"""
import asyncio
import os
from pathlib import Path
from typing import Optional
from dotenv import set_key, load_dotenv
from axiomtradeapi import AxiomTradeClient


load_dotenv()


def save_tokens_to_env(client):
    """
    Save refreshed authentication tokens back to .env file for persistence.
    
    Args:
        client: AxiomTradeClient instance with valid tokens
        
    Returns:
        bool: True if tokens were saved successfully, False otherwise
    """
    try:
        # Find the .env file path
        env_path = Path('.env')
        if not env_path.exists():
            print("⚠️  .env file not found, tokens not saved to file")
            return False
        
        # Get current tokens from client
        tokens = client.auth_manager.get_tokens()
        if not tokens:
            return False
        
        # Update the .env file
        set_key(env_path, 'AXIOM_AUTH_TOKEN', tokens.access_token)
        set_key(env_path, 'AXIOM_REFRESH_TOKEN', tokens.refresh_token)
        
        return True
    except Exception as e:
        print(f"⚠️  Failed to save tokens to .env: {e}")
        return False

def create_authenticated_client() -> Optional[AxiomTradeClient]:
    """
    Create an XHR client for making HTTP requests.
    
    Returns:
        AxiomTradeClient instance
    """
    client = AxiomTradeClient(
        auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
        refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
    )
    # Ensure we have fresh tokens
    if not client.ensure_authenticated():
        print("⚠️ Connection failed")
        print("🔄 Attempting to refresh access token...")
        # Try to refresh the token
        if client.refresh_access_token():
            print("✅ Token refreshed successfully!")
            
            # Save the new tokens to .env file
            if save_tokens_to_env(client):
                print("💾 New tokens saved to .env file")
        else:
            print("❌ Failed to refresh token")
            print("💡 TIP: Copy fresh tokens from browser and update your .env file")
            return None

    token_info = client.get_token_info_detailed()
    print(f"✅ Authenticated. Token expires in {token_info.get('time_until_expiry', 'unknown')}")

    return client

async def connect_with_retry( subscribe_func, max_retries=2):
    """
    Connect to WebSocket with automatic retry and token refresh.
    
    This function handles the common pattern of:
    1. Attempting to subscribe to a WebSocket channel
    2. If connection fails (401), refresh the access token
    3. Save the new tokens to .env
    4. Retry the connection
    
    Args:
        client: AxiomTradeClient instance
        subscribe_func: Async function that performs the subscription
                       Should return True on success, False on failure
        max_retries: Maximum number of connection attempts (default: 2)
        
    Returns:
        tuple: (success: bool, ws_client: WebSocketClient or None)
    
    Example:
        async def do_subscribe(ws_client):
            return await ws_client.subscribe_new_tokens(callback=my_callback)
        
        success, ws_client = await connect_with_retry(client, do_subscribe)
        if success:
            await ws_client.start()
    """

    # Initialize with authentication
    client = AxiomTradeClient(
        auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
        refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
    )
    
    print("🔍 Connecting to WebSocket...")
    print("Press Ctrl+C to stop\n")
    
    # Ensure we have fresh tokens
    if not client.ensure_authenticated():
        print("❌ Failed to authenticate. Please check your tokens.")
        return

    token_info = client.get_token_info_detailed()
    print(f"✅ Authenticated. Token expires in {token_info.get('time_until_expiry', 'unknown')}")
    
    retry_count = 0
    success = False
    ws_client = client.get_websocket_client()
    
    while retry_count < max_retries and not success:
        # Attempt subscription
        success = await subscribe_func(ws_client)
        
        if not success:
            retry_count += 1
            if retry_count < max_retries:
                print(f"⚠️  Connection failed (attempt {retry_count}/{max_retries})")
                print("🔄 Attempting to refresh access token...")
                
                # Try to refresh the token
                if client.refresh_access_token():
                    print("✅ Token refreshed successfully!")
                    
                    # Save the new tokens to .env file
                    if save_tokens_to_env(client):
                        print("💾 New tokens saved to .env file")
                    
                    # Create a new WebSocket client with fresh tokens
                    ws_client = client.get_websocket_client()
                    await asyncio.sleep(1)  # Brief pause before retry
                else:
                    print("❌ Failed to refresh token")
                    print("💡 TIP: Copy fresh tokens from browser and update your .env file")
                    break
            else:
                print(f"❌ Failed to connect after {max_retries} attempts")
    
    return success, ws_client, client if success else None
