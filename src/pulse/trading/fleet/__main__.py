"""
Main entry point for the Shadow Fleet.
- Connects to Pulse & SOL Price WebSockets.
- Feeds data to PulseTracker.
- Orchestrates the ShadowFleetManager.
"""
import asyncio
import argparse
from src.pulse.trading.fleet.pulse_websocket_feed import PulseWebsocketFeed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Axiom Pulse Terminal Bot")
    parser.add_argument("--baseline", action="store_true", help="Run the simplified baseline strategy instead of the complex core strategy")
    args = parser.parse_args()

    feed = PulseWebsocketFeed(baseline_mode=args.baseline)
    try:
        asyncio.run(feed.run())
    except KeyboardInterrupt:
        pass
