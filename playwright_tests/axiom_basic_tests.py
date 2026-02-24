from playwright.sync_api import Page, expect
import time
import re
import json
import msgpack
import sys
import os

# Make src importable from playwright_tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.pulse.decoder import PulseDecoder
from src.pulse.tracker import PulseTracker

def test_navigate_to_pulse(page: Page):
    """Test clicking the Pulse button and navigating to pulse page."""
    
    print(f"\n🔍 Page URL at start: {page.url}")
    print(f"🔍 Page object type: {type(page)}")
    
    page.goto("https://axiom.trade/")
    page.wait_for_load_state("domcontentloaded")
    
    print(f"✅ Page loaded: {page.url}")
    
    # Sleep to see the browser state before clicking
    print("⏸️  Sleeping 3 seconds so you can see the page...")
    time.sleep(3)
    
    # FIX: Use .first to select the first matching button
    # (There are 2 "Pulse" buttons on the page - sidebar + mobile menu)
    pulse_button = page.get_by_role("button", name="Pulse").first
    
    print("🔍 Found Pulse button, checking visibility...")
    expect(pulse_button).to_be_visible()
    
    print("🖱️  Clicking Pulse button...")
    pulse_button.click()
    
    print("⏳ Waiting for navigation to pulse page...")
    page.wait_for_url("**/pulse**", timeout=10000)
    
    # FIX: Use regex pattern instead of lambda
    expect(page).to_have_url(re.compile(".*pulse.*"))
    
    print(f"✅ Successfully navigated to: {page.url}")
    
    # Sleep again so you can see the result
    print("⏸️  Sleeping 3 seconds so you can see pulse page...")
    time.sleep(3)


def test_connect_pulse_websocket(page: Page):
    """Test connecting to the Pulse websocket and capturing data."""
    
    # Storage for WebSocket data
    pulse_websocket = None
    websocket_messages = []
    
    # Listen for WebSocket connections
    def on_websocket(ws):
        # FILTER: Only listen to the Pulse WebSocket
        if "pulse2.axiom.trade/ws" in ws.url:
            nonlocal pulse_websocket
            pulse_websocket = ws
            print(f"\n🔌 Pulse WebSocket connected: {ws.url}")
            
            # Listen for frames (messages) sent TO server
            ws.on("framesent", lambda payload: 
                print(f"📤 Sent: {payload[:100]}...") if len(str(payload)) > 100 else print(f"📤 Sent: {payload}"))
            
            # Listen for frames (messages) received FROM server
            ws.on("framereceived", lambda payload: 
                on_frame_received(payload))
            
            # Listen for close
            ws.on("close", lambda: print(f"❌ Pulse WebSocket closed"))
        else:
            # Ignore other WebSockets
            print(f"ℹ️  Ignoring WebSocket: {ws.url}")
    
    def on_frame_received(payload):
        """Handle received WebSocket messages from Pulse"""
        nonlocal websocket_messages
        payload_str = str(payload)
        print(f"📥 Pulse message: {payload_str[:200]}..." if len(payload_str) > 200 else f"📥 Pulse message: {payload_str}")
        websocket_messages.append(payload)
    
    # Attach the WebSocket listener BEFORE navigating
    page.on("websocket", on_websocket)
    
    print("\n🚀 Navigating to Pulse page...")
    page.goto('https://axiom.trade/pulse')
    page.wait_for_load_state("domcontentloaded")
    
    print(f"✅ Page loaded: {page.url}")
    
    # Wait for WebSocket to connect and receive messages
    print("\n⏳ Waiting 10 seconds to capture Pulse WebSocket data...")
    print("=" * 60)
    # CRITICAL: Use page.wait_for_timeout() instead of time.sleep()
    # This keeps Playwright's event loop running so WebSocket events fire in real-time
    page.wait_for_timeout(10000)  # 10 seconds in milliseconds
    print("=" * 60)
    
    # Summary
    print(f"\n📊 Pulse WebSocket Summary:")
    
    if pulse_websocket:
        print(f"✅ Connected to: {pulse_websocket.url}")
        print(f"📊 Total messages received: {len(websocket_messages)}")
    else:
        print("❌ Pulse WebSocket NOT connected")
    
    if websocket_messages:
        print(f"\n🎉 Successfully received {len(websocket_messages)} Pulse messages!")
        print("\n📦 First message:")
        print(websocket_messages[0])
        
        if len(websocket_messages) > 1:
            print("\n📦 Last message:")
            print(websocket_messages[-1])
    else:
        print("\n⚠️  No Pulse messages received")
    
    # Keep browser open a bit longer
    print("\n⏸️  Keeping browser open 5 more seconds...")
    page.wait_for_timeout(5000)


def test_browser_pulse_provider(page: Page):
    """
    Integration test: verifies the full browser → decoder → tracker pipeline.

    This is the foundation for BrowserPulseProvider:
    - Captures Pulse binary messages from wss://pulse2.axiom.trade/ws
    - Decodes them with msgpack + PulseDecoder
    - Feeds decoded data into PulseTracker
    - Captures SOL price from wss://cluster6.axiom.trade/ (room: sol_price)
    - Asserts tracker state is populated after snapshot
    """

    # --- Pipeline setup ---
    tracker = PulseTracker()

    # Capture results
    results = {
        "pulse_raw_count": 0,       # raw bytes received
        "pulse_decoded_count": 0,   # successfully decoded
        "pulse_decode_errors": [],  # any decode failures
        "sol_price": None,          # latest SOL price float
        "sol_price_count": 0,       # how many SOL price messages
    }

    # --- WebSocket handlers ---
    def on_websocket(ws):
        if "pulse2.axiom.trade/ws" in ws.url:
            print(f"\n🔌 [Pulse] Connected: {ws.url}")
            ws.on("framereceived", on_pulse_frame)
            ws.on("close", lambda: print("❌ [Pulse] WebSocket closed"))

        elif "cluster9.axiom.trade" in ws.url:
            print(f"\n🔌 [SOL] Connected: {ws.url}")
            ws.on("framereceived", on_sol_frame)
            ws.on("close", lambda: print("❌ [SOL] WebSocket closed"))

        else:
            print(f"ℹ️  Ignoring: {ws.url}")

    def on_pulse_frame(payload):
        """Decode raw bytes → msgpack → PulseDecoder → PulseTracker"""
        if not isinstance(payload, bytes):
            return

        results["pulse_raw_count"] += 1

        try:
            # Step 1: unpack MessagePack bytes (same as handler.py)
            decoded = msgpack.unpackb(payload, raw=False)

            # Step 2: feed into tracker (which uses PulseDecoder internally)
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(tracker.process_message(decoded))
            loop.close()

            results["pulse_decoded_count"] += 1

            msg_type = decoded[0] if isinstance(decoded, (list, tuple)) else "?"
            token_count = len(tracker.tokens)
            print(f"📥 [Pulse] Type={msg_type} | Tokens tracked: {token_count}")

        except Exception as e:
            results["pulse_decode_errors"].append(str(e))
            print(f"⚠️  [Pulse] Decode error: {e}")

    def on_sol_frame(payload):
        """Parse SOL price JSON message"""
        try:
            # SOL price messages are JSON text, not binary
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            data = json.loads(payload)

            if data.get("room") == "sol_price":
                price = float(data["content"])
                results["sol_price"] = price
                results["sol_price_count"] += 1
                print(f"💰 [SOL] Price: ${price:.4f}")

        except Exception as e:
            print(f"⚠️  [SOL] Parse error: {e} | raw: {str(payload)[:100]}")

    # --- Navigate and capture ---
    page.on("websocket", on_websocket)

    print("\n🚀 Navigating to axiom.trade/pulse...")
    page.goto("https://axiom.trade/pulse")
    page.wait_for_load_state("domcontentloaded")
    print(f"✅ Page loaded: {page.url}")

    print("\n⏳ Capturing for 15 seconds...")
    print("=" * 60)
    page.wait_for_timeout(15000)
    print("=" * 60)

    # --- Assertions ---
    print("\n📊 Pipeline Summary:")
    print(f"   Pulse raw messages:    {results['pulse_raw_count']}")
    print(f"   Pulse decoded:         {results['pulse_decoded_count']}")
    print(f"   Pulse decode errors:   {len(results['pulse_decode_errors'])}")
    print(f"   Tokens in tracker:     {len(tracker.tokens)}")
    print(f"   SOL price messages:    {results['sol_price_count']}")
    print(f"   Latest SOL price:      {results['sol_price']}")

    if results["pulse_decode_errors"]:
        print("\n⚠️  Decode errors:")
        for err in results["pulse_decode_errors"][:5]:
            print(f"   - {err}")

    # Assert Pulse pipeline works
    assert results["pulse_raw_count"] > 0, "❌ No Pulse binary messages received"
    assert results["pulse_decoded_count"] > 0, "❌ No messages decoded successfully"
    assert len(tracker.tokens) > 0, "❌ PulseTracker has no tokens after snapshot"

    # Assert SOL price pipeline works
    assert results["sol_price_count"] > 0, "❌ No SOL price messages received"
    assert results["sol_price"] is not None, "❌ SOL price is None"
    assert isinstance(results["sol_price"], float), "❌ SOL price is not a float"
    assert results["sol_price"] > 0, f"❌ SOL price is not positive: {results['sol_price']}"

    print(f"\n✅ Pipeline verified!")
    print(f"   {len(tracker.tokens)} tokens tracked")
    print(f"   SOL @ ${results['sol_price']:.4f}")