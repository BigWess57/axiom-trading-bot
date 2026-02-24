"""
Dashboard connector for trading bot
"""
import logging
from typing import Dict, Any, List
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from src.pulse_dashboard.models import BotState

# --- Dashboard Connector ---
class DashboardConnector:
    """
    Handles communication between the trading bot and the dashboard API.
    """
    def __init__(self, api_url: str = "http://localhost:8000/api/bot/state"):
        self.api_url = api_url
        self.session = None

    async def _get_session(self):
        """Get or create a shared session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def send_update(self, state: Dict[str, Any]):
        """
        Send bot state update to the dashboard.
        Silently fails on connection errors to avoid disrupting the bot.
        """
        try:
            session = await self._get_session()
            async with session.post(self.api_url, json=state) as response:
                if response.status != 200:
                    logger.warning(f"Failed to send dashboard update: {response.status}")
        except Exception as e:
            # We log at debug level to not spam logs if dashboard is down
            logger.debug(f"Could not connect to dashboard: {e}")

    async def close(self):
        """Close the dashboard connector."""
        if self.session:
            await self.session.close()
