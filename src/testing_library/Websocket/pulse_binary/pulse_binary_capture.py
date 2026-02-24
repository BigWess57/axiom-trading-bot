#!/usr/bin/env python3
"""
Pulse Binary WebSocket - Capture data from wss://pulse2.axiom.trade/ws

This endpoint streams real-time Pulse data in compressed binary format.
"""
import asyncio
import json
import time
from src.utils.connection_helpers import connect_with_retry
from src.config.pulse_filters import DEFAULT_PULSE_FILTERS
from axiomtradeapi.websocket.client import AxiomTradeWebSocketClient

async def capture_pulse_messages():
    """Connect to pulse2.axiom.trade and capture binary messages"""
    
    print("🔌 Subscribing to Pulse WebSocket...")
    async def do_subscribe(ws_client: AxiomTradeWebSocketClient):
        return await ws_client.subscribe_to_pulse(
            filters=DEFAULT_PULSE_FILTERS,
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client = await connect_with_retry(do_subscribe)

    if success:
        try:
            print(f"📥 Capturing messages for 65 seconds...\n")
            
            messages = []
            start_time = time.time()
            duration = 65
            message_count = 0
            
            while time.time() - start_time < duration:
                try:
                    # Use a short timeout to check the loop condition frequently
                    msg = await asyncio.wait_for(ws_client.ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                    
                message_count += 1
                i = message_count - 1 # 0-based index for compatibility
                
                print(f"--- Message {message_count} ---")
                print(f"Type: {type(msg).__name__}")
                print(f"Size: {len(msg) if isinstance(msg, (str, bytes)) else 'N/A'} bytes/chars")
                
                if isinstance(msg, str):
                    # Text message (likely JSON)
                    print(f"✅ TEXT: {msg[:500]}")
                    try:
                        parsed = json.loads(msg)
                        messages.append({"type": "json", "data": parsed})
                        print(f"📦 Parsed: {parsed}")
                    except:
                        messages.append({"type": "text", "data": msg})
                
                elif isinstance(msg, bytes):
                    # Binary - try to decode
                    print(f"Hex preview: {msg[:100].hex()}")
                    
                    try:
                        # Try UTF-8 decode
                        text = msg.decode('utf-8')
                        print(f"✅ UTF-8: {text[:500]}")
                        try:
                            parsed = json.loads(text)
                            messages.append({"type": "json", "data": parsed})
                        except:
                            messages.append({"type": "text", "data": text})
                    except:
                        # Try MessagePack
                        try:
                            import msgpack
                            unpacked = msgpack.unpackb(msg, raw=False)
                            print(f"✅ MessagePack: {unpacked}")
                            messages.append({"type": "msgpack", "data": unpacked})
                        except Exception as e:
                            print(f"❌ Could not decode: {e}")
                            messages.append({"type": "binary", "hex": msg.hex()})
                
                print()
            
            await ws_client.close()
            
            # Save to file
            output_file = "pulse_messages.json"
            with open(output_file, "w") as f:
                json.dump(messages, f, indent=2)
            
            print(f"\n✅ Saved {len(messages)} messages to {output_file}")
            
            # Print summary
            print("\n📊 Summary:")
            print(f"   JSON messages: {sum(1 for m in messages if m['type'] == 'json')}")
            print(f"   Text messages: {sum(1 for m in messages if m['type'] == 'text')}")
            print(f"   MessagePack: {sum(1 for m in messages if m['type'] == 'msgpack')}")
            print(f"   Binary: {sum(1 for m in messages if m['type'] == 'binary')}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(capture_pulse_messages())
    except KeyboardInterrupt:
        print("\nStopped by user")
