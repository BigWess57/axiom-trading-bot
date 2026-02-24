"""
Main entry point for the Shadow Fleet.
- Connects to Pulse & SOL Price WebSockets.
- Feeds data to PulseTracker.
- Orchestrates the ShadowFleetManager.
"""
import asyncio
from src.pulse.trading.fleet.pulse_websocket_feed import PulseWebsocketFeed

if __name__ == "__main__":
    feed = PulseWebsocketFeed()
    try:
        asyncio.run(feed.run())
    except KeyboardInterrupt:
        pass
