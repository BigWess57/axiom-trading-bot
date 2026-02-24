"""
WebSocket frame interceptors for Pulse and SOL price feeds.

Each interceptor is a factory that returns a handler bound to a shared queue,
so the provider can attach them to Playwright WebSocket events.

Message formats:
- Pulse (pulse2.axiom.trade/ws): binary MessagePack frames
- SOL price (cluster9.axiom.trade): JSON text frames, room="sol_price"
"""
import json
import logging
import asyncio
from typing import Callable

import msgpack

from .endpoints import Websockets

logger = logging.getLogger(__name__)


def make_pulse_handler(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> Callable:
    """
    Returns a framereceived handler for wss://pulse2.axiom.trade/ws.

    Decodes MessagePack bytes and puts ("pulse", decoded_data) onto the queue.
    Errors are logged and swallowed so the browser keeps running.
    """
    def on_pulse_frame(payload: bytes) -> None:
        if not isinstance(payload, bytes):
            return
        try:
            decoded = msgpack.unpackb(payload, raw=False)
            asyncio.run_coroutine_threadsafe(queue.put(("pulse", decoded)), loop)
        except Exception as e:
            logger.warning("Pulse decode error: %s", e)

    return on_pulse_frame


def make_sol_price_handler(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> Callable:
    """
    Returns a framereceived handler for wss://cluster9.axiom.trade/.

    Parses JSON frames and puts ("sol_price", float) onto the queue
    when room == "sol_price".
    """
    def on_sol_frame(payload) -> None:
        try:
            if isinstance(payload, bytes):
                payload_str = payload.decode("utf-8")
            else:
                payload_str = payload

            data = json.loads(payload_str)

            if data.get("room") == "sol_price":
                price = float(data["content"])
                asyncio.run_coroutine_threadsafe(queue.put(("sol_price", price)), loop)

        except Exception as e:
            logger.warning("SOL price parse error: %s | raw: %.100s", e, str(payload))

    return on_sol_frame


def attach_interceptors(page, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
    """
    Attach WebSocket interceptors to a Playwright page before navigation.

    Must be called BEFORE page.goto() so no WebSocket connections are missed.
    """
    pulse_handler = make_pulse_handler(queue, loop)
    sol_handler = make_sol_price_handler(queue, loop)

    def on_websocket(ws):
        url = ws.url
        if Websockets.PULSE in url:
            logger.info("Pulse WebSocket connected: %s", url)
            ws.on("framereceived", pulse_handler)
            ws.on("close", lambda: logger.warning("Pulse WebSocket closed"))

        elif Websockets.MAIN in url:
            logger.info("SOL price WebSocket connected: %s", url)
            ws.on("framereceived", sol_handler)
            ws.on("close", lambda: logger.warning("SOL price WebSocket closed"))

        else:
            logger.debug("Ignoring WebSocket: %s", url)

    page.on("websocket", on_websocket)
