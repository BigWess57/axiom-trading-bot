import time
import json
import msgpack
import sys
import os
from playwright.sync_api import Page, expect
from dateutil import parser as date_parser
from datetime import datetime

# Make src importable from playwright_tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.pulse.decoder import PulseDecoder
from src.pulse.tracker import PulseTracker
from playwright_stealth_browser.api_client import StealthApiClient
from playwright_stealth_browser.api_templates import ApiTemplates

def test_integration_pulse_and_rest(page: Page):
    """
    Integration test: verifies the full browser websocket pipeline and 
    subsequent REST API calls using StealthApiClient for discovered tokens.
    """
    class DummyProvider:
        def __init__(self, page):
            self.page = page
        def evaluate_js(self, js_code):
            return self.page.evaluate(js_code)
            
    tracker = PulseTracker()
    client = StealthApiClient(DummyProvider(page))
    
    # Track when the websocket connection is ready
    pulse_connected = False
    
    def on_websocket(ws):
        if "pulse2.axiom.trade/ws" in ws.url:
            nonlocal pulse_connected
            pulse_connected = True
            print(f"\n🔌 [Pulse] Connected to WebSocket: {ws.url}")
            ws.on("framereceived", on_pulse_frame)
            ws.on("close", lambda: print("❌ [Pulse] WebSocket closed"))

    def on_pulse_frame(payload):
        """Decode raw bytes → msgpack → PulseDecoder → PulseTracker"""
        if not isinstance(payload, bytes):
            return

        try:
            decoded = msgpack.unpackb(payload, raw=False)
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(tracker.process_message(decoded))
            loop.close()
        except Exception as e:
            print(f"⚠️  [Pulse] Decode error: {e}")

    # Set up listener before navigation
    page.on("websocket", on_websocket)

    print("\n🚀 Navigating to axiom.trade/pulse to capture tokens...")
    page.goto("https://axiom.trade/pulse")
    page.wait_for_load_state("domcontentloaded")
    print(f"✅ Page loaded: {page.url}")

    # Wait for tracker to buffer tokens from the websocket stream
    print("\n⏳ Listening to Pulse WebSocket for 6 seconds...")
    page.wait_for_timeout(6000)
    
    # Assert we caught some tokens
    tracked_tokens = list(tracker.tokens.keys())
    token_count = len(tracked_tokens)
    print(f"\n✅ Finished listening. Captured {token_count} total tokens.")
    assert token_count > 0, "No tokens were captured from the Pulse WebSocket!"
    
    print("\n🔄 Beginning StealthApiClient REST iteration over captured tokens...")
    print("=" * 70)
    
    # Get current timestamp for the chart query
    now_ms = int(time.time() * 1000)
    
    tested_count = 0
    
    # FIRE NATIVE JAVASCRIPT ORCHESTRATION 
    # All 20 tokens will be processed entirely by chromium's V8 engine concurrently
    start_time = time.time()
    batch_results = client.get_full_token_analysis_batch(tracked_tokens)
    elapsed_time = time.time() - start_time
    print(f"\n⏱️ Native JS Batch orchestration took {elapsed_time:.2f} seconds to fetch {token_count * 4} endpoints for {token_count} tokens")
    
    # Iterate through the returned python dictionary mapping to verify data integrity
    for pair_address, data in batch_results.items():
        tested_count += 1
        print(f"\n[{tested_count}/{token_count}] Verifying API Suite for pair: {pair_address}")
        
        tx_data = data.get("tx_data", {})
        pair_info = data.get("pair_info", {})
        chart_data = data.get("chart_data", {})
        holder_data = data.get("holder_data", {})
        
        # 1. get_last_transaction
        assert tx_data is not None, f"get_last_transaction returned None for {pair_address}"
        assert "error" not in tx_data, f"Error in last_transaction: {tx_data.get('error')}"
        print(f"      ✅ TX Success. Keys found: {list(tx_data.keys())[:5]}")
        
        # 2. get_pair_info
        assert pair_info is not None, f"get_pair_info returned None for {pair_address}"
        assert "error" not in pair_info, f"Error in get_pair_info: {pair_info.get('error')}"
        token_name = pair_info.get("tokenName", "Unknown")
        print(f"      ✅ Info Success. Resolved name: {token_name}")
        
        # 3. get_pair_chart
        assert chart_data is not None, f"get_pair_chart returned None for {pair_address}"
        assert "error" not in chart_data, f"Error in get_pair_chart: {chart_data.get('error')}"
        candles = chart_data.get("bars", []) or chart_data.get("candles", [])
        print(f"      ✅ Chart Success. Fetched {len(candles)} candles.")
        
        # 4. get_holder_data
        assert holder_data is not None, f"get_holder_data returned None for {pair_address}"
        assert "error" not in holder_data, f"Error in get_holder_data: {holder_data.get('error')}"
        holders = holder_data.get("items", []) if isinstance(holder_data, dict) else holder_data
        print(f"      ✅ Holder Success. Fetched {len(holders)} holders.")
        
    print("\n" + "=" * 70)
    print(f"🎉 SUCCESS! Orchestrated {tested_count * 4} API requests concurrently across {token_count} websocket tokens")
