"""
Pulse Dashboard Server — Browser Feed Edition

Replaces the direct WebSocket connections with a stealth browser
(BrowserPulseProvider) that intercepts Pulse and SOL price feeds.
"""
import asyncio
import logging
import dataclasses
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any, Dict

import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from playwright_stealth_browser import BrowserPulseProvider

from src.pulse.tracker import PulseTracker, PulseToken
from src.pulse_dashboard.models import BotState
from src.utils.async_utils import bridge_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseServer")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize_token(token: PulseToken) -> Dict[str, Any]:
    """Serialize a PulseToken to a JSON-safe dictionary."""
    data = dataclasses.asdict(token)
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    if "raw_fields" in data and data["raw_fields"]:
        data["raw_fields"] = {
            str(k): (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in data["raw_fields"].items()
        }
    return data


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

tracker = PulseTracker()
current_sol_price: float | None = None
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


# ---------------------------------------------------------------------------
# Socket.IO event emitters (called by tracker callbacks and provider)
# ---------------------------------------------------------------------------

async def on_token_update(token: PulseToken) -> None:
    await sio.emit("token_update", serialize_token(token))

async def on_new_token(token: PulseToken) -> None:
    logger.info("New Token: %s", token.ticker)
    await sio.emit("new_token", serialize_token(token))

async def on_token_removed(category: str, pair_address: str) -> None:
    logger.info("Token Removed: %s %s", category, pair_address[:6])
    await sio.emit("token_removed", {"category": category, "pair_address": pair_address})

async def on_sol_price_update(price: float) -> None:
    global current_sol_price
    current_sol_price = price
    logger.debug("SOL Price: $%.3f", price)
    await sio.emit("sol_price", {"price": price, "timestamp": datetime.utcnow().isoformat()})


# ---------------------------------------------------------------------------
# Lifespan — starts the browser provider and consume loop
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Wire tracker callbacks so events flow to Socket.IO
    tracker.on_update = bridge_callback(on_token_update)
    tracker.on_new_token = bridge_callback(on_new_token)
    tracker.on_token_removed = bridge_callback(on_token_removed)

    # Create and start the browser provider.
    # start() must be called here (inside the running event loop) so that
    # asyncio.get_event_loop() inside start() returns the correct loop.
    provider = BrowserPulseProvider()
    provider.start()

    # Launch the consume loop as a background task so it doesn't block startup.
    # It will run for the lifetime of the server, feeding data into the tracker.
    consume_task = asyncio.create_task(
        provider.consume(
            pulse_cb=tracker.process_message,
            sol_price_cb=on_sol_price_update,
        )
    )

    logger.info("Browser feed started — waiting for Pulse data...")

    yield  # Server is running

    # Shutdown: stop the provider (signals the browser thread and the consume loop)
    provider.stop()
    consume_task.cancel()


# ---------------------------------------------------------------------------
# FastAPI + Socket.IO app
# ---------------------------------------------------------------------------

fastapi_app = FastAPI(lifespan=lifespan)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@fastapi_app.get("/health")
def health():
    return {"status": "ok", "tokens": len(tracker.tokens), "sol_price": current_sol_price}

@fastapi_app.get("/api/tokens")
def get_tokens():
    return [serialize_token(t) for t in tracker.get_all_tokens()]

@fastapi_app.get("/api/tokens/{pair_address}")
def get_token(pair_address: str):
    token = tracker.tokens.get(pair_address)
    if not token:
        return {"error": "Token not found"}
    return serialize_token(token)

@fastapi_app.get("/api/candles/{pair_address}")
def get_candles(pair_address: str):
    """Candles endpoint — requires axiom_client (HTTP).
    Not available in browser-feed mode without a separate HTTP client setup."""
    return {"error": "Candles not available in browser-feed mode"}

@fastapi_app.post("/api/bot/state")
async def update_bot_state(state: BotState):
    await sio.emit("bot_state_update", state.model_dump())
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Socket.IO connection handlers
# ---------------------------------------------------------------------------

@sio.event
async def connect(sid, environ):
    logger.info("Connected: %s", sid)
    # Send current snapshot to the newly connected client
    tokens = [serialize_token(t) for t in tracker.get_all_tokens()]
    tokens.sort(key=lambda x: x.get("created_at", "") or "", reverse=True)
    await sio.emit("snapshot", tokens, to=sid)
    if current_sol_price is not None:
        await sio.emit("sol_price", {
            "price": current_sol_price,
            "timestamp": datetime.utcnow().isoformat(),
        }, to=sid)

@sio.event
async def disconnect(sid):
    logger.info("Disconnected: %s", sid)

@sio.on("request_snapshot")
async def on_request_snapshot(sid):
    logger.info("Snapshot requested by: %s", sid)
    tokens = [serialize_token(t) for t in tracker.get_all_tokens()]
    tokens.sort(key=lambda x: x.get("created_at", "") or "", reverse=True)
    await sio.emit("snapshot", tokens, to=sid)
    if current_sol_price is not None:
        await sio.emit("sol_price", {
            "price": current_sol_price,
            "timestamp": datetime.utcnow().isoformat(),
        }, to=sid)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "src.pulse_dashboard.server.api_with_browser_feed:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # reload=True would conflict with the browser thread
    )