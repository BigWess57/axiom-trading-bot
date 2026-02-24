"""
Test Pulse WebSocket Subscription
Verifies that subscribe_to_pulse connects and counts messages correctly.
"""
import asyncio
from src.utils.connection_helpers import connect_with_retry
# Import filters from config
from src.config.pulse_filters import DEFAULT_PULSE_FILTERS
from axiomtradeapi.websocket.client import AxiomTradeWebSocketClient

async def test_pulse_subscription():
    """Test the Pulse WebSocket subscription"""
    
    # Track last reported count
    last_count = [0]
    
    def on_message_count(count):
        if count % 10 == 0 or count != last_count[0] + 1:  # Report every 10 messages or on gaps
            print(f"📊 Messages received: {count}")
            last_count[0] = count
    
    print("🔌 Subscribing to Pulse WebSocket...")
    async def do_subscribe(ws_client: AxiomTradeWebSocketClient):
        return await ws_client.subscribe_to_pulse(
            filters=DEFAULT_PULSE_FILTERS,
            count_callback=on_message_count
        )
    
    # Connect with automatic retry and token refresh
    success, ws_client, _ = await connect_with_retry(do_subscribe)
    
    if success:
        print("✅ Connected and subscribed to pulse!")
        
        # Start message handler as a task (non-blocking)
        handler_task = asyncio.create_task(ws_client.ensure_connection_and_listen())
        
        try:
            print("📊 Monitoring for 10 seconds (press Ctrl+C to stop early)...\n")
            await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\n\n⏸️  Stopped by user")
        finally:
            # Cancel the message handler
            handler_task.cancel()
            try:
                await handler_task
            except asyncio.CancelledError:
                pass  # Expected when we cancel
            
            # Get final count
            final_count = ws_client.get_pulse_message_count()
            print(f"\n📈 Final Statistics:")
            print(f"   Total messages received: {final_count}")
            print(f"   Average: {final_count / 10:.1f} messages/second")
            
            # Close WebSocket
            if ws_client.ws:
                await ws_client.ws.close()
    else:
        print("❌ Could not establish WebSocket connection")

if __name__ == "__main__":
    try:
        asyncio.run(test_pulse_subscription())
    except KeyboardInterrupt:
        print("\n\n⏸️  Stopped by user")