
import asyncio
import logging
import websockets
import os
import ssl
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManualCookieTest")

async def test_connection():
    uri = "wss://pulse2.axiom.trade/ws"
    
    # print(f"\n⚠️  PASTE YOUR FULL WEBSOCKET URL BELOW (Default: {uri}) ⚠️")
    # print("In Chrome: Network Tab -> WS -> Headers -> Request URL")
    # print("Example: wss://pulse2.axiom.trade/ws?token=...")
    # uri_input = input("WebSocket URL: ").strip()
    # if uri_input:
    #     uri = uri_input
    
    print("\n⚠️  PASTE COOKIES FROM A SUCCESSFUL API REQUEST (XHR) ⚠️")
    print("Look for 'cf_clearance' or '__cf_bm' in the Cookie header.")
    print("In Chrome: Network Tab -> Fetch/XHR -> Select any request -> Headers -> Request Headers -> Cookie")
    cookie_string = input("Cookie: ").strip()
    
    print("\n⚠️  PASTE YOUR USER-AGENT STRING BELOW ⚠️")
    print("Should look like: Mozilla/5.0 ...")
    user_agent_input = input("User-Agent: ").strip()
    
    user_agent = user_agent_input if user_agent_input else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"

    headers = {
        'Origin': "https://axiom.trade",
        'Cache-Control': 'no-cache',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Pragma': 'no-cache',
        'User-Agent': user_agent,
        'Cookie': cookie_string
    }

    print(f"\n🔍 Connecting to {uri} with CUSTOM SSL CONTEXT...")
    for k, v in headers.items():
        print(f"  {k}: {v[:50]}..." if len(v) > 50 else f"  {k}: {v}")

    # Custom SSL Context to mimic Browser
    ssl_context = ssl.create_default_context()
    
    # 1. Force TLSv1.2 or higher
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # 2. Set strict ciphers (Chrome-like) - Removing generic ones might help avoid fingerprinting
    # This list mimics a modern Chrome cipher suite
    ciphers = "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
    ssl_context.set_ciphers(ciphers)
    
    # 3. Set ALPN protocols (Crucial for Cloudflare to treat this as legitimate traffic)
    ssl_context.set_alpn_protocols(["http/1.1"])

    try:
        async with websockets.connect(uri, additional_headers=headers, ssl=ssl_context) as websocket:
            print("\n✅ CONNECTED SUCCESSFULLY!")
            print("Server accepted the connection.")
            
            # Subscribing to pulse
            msg = {
                "topic": "subscribe",
                "channel": "pulse"
            }
            # For pulse it might be binary or json? The original code uses msgpack for pulse.
            # But let's just see if we stay connected.
            
            print("Listening for messages (Ctrl+C to stop)...")
            while True:
                response = await websocket.recv()
                print(f"📩 Received: {len(response)} bytes")
                
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print("\nStopped.")
