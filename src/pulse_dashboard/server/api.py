"""
Pulse Dashboard Server
"""
import asyncio
import logging
import dataclasses
from datetime import datetime
from dateutil import parser as date_parser
from contextlib import asynccontextmanager
from typing import Any, Dict

import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from axiomtradeapi.websocket.client import AxiomTradeWebSocketClient, WebSocketMode
from src.pulse.tracker import PulseTracker, PulseToken
from src.config.pulse_filters import DEFAULT_PULSE_FILTERS
from src.utils.connection_helpers import connect_with_retry
from src.pulse_dashboard.models import BotState
from src.utils.async_utils import bridge_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseServer")

def serialize_token(token: PulseToken) -> Dict[str, Any]:
    """Serialize a PulseToken to a dictionary."""
    data = dataclasses.asdict(token)
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    
    # Ensure raw_fields values are JSON-serializable
    if 'raw_fields' in data and data['raw_fields']:
        data['raw_fields'] = {
            str(k): (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in data['raw_fields'].items()
        }
    
    return data

tracker = PulseTracker()
ws_client = None  # Pulse WebSocket client
axiom_client = None # HTTP Client for API requests
ws_client_sol_price = None  # SOL price WebSocket client
ws_client_token_price = None # Token price WebSocket client
bg_task = None  # Pulse background task
bg_task_token_price = None # Token price background task
bg_task_sol_price = None  # SOL price background task
current_sol_price = None  # Latest SOL price
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')



async def on_token_update(token: PulseToken):
    """Emit token update event."""
    await sio.emit('token_update', serialize_token(token))

async def on_new_token(token: PulseToken):
    """Emit new token event."""
    logger.info(f"New Token: {token.ticker}")
    await sio.emit('new_token', serialize_token(token))

async def on_token_removed(category: str, pair_address: str):
    """Emit token removed event."""
    logger.info(f"Token Removed: {category} {pair_address[:6]}")
    await sio.emit('token_removed', {'category': category, 'pair_address': pair_address})

async def on_sol_price_update(price: float):
    """Emit SOL price update event."""
    global current_sol_price
    current_sol_price = price
    logger.debug(f"SOL Price: ${price:.3f}")
    await sio.emit('sol_price', {'price': price, 'timestamp': datetime.utcnow().isoformat()})

# --- Price Subscription Handling ---

def create_price_handler(pair_address: str):
    """Create a callback handler for a specific token."""
    async def handler(data: Dict[str, Any]):
        # Data usually contains {price: ..., ...} directly from 'token_price' event
        # We forward it to the room
        await sio.emit('price_update', data, room=f"price_{pair_address}")
        # logger.info(f"Price Update: {pair_address} {data.get('price_usd')} {data.get('created_at')}")
    return handler

@sio.on('subscribe_price')
async def on_subscribe_price(sid, pair_address: str):
    """Handle client subscription to token price."""
    room_name = f"price_{pair_address}"
    logger.info(f"Client {sid} subscribing to {pair_address}")
    await sio.enter_room(sid, room_name)
    logger.info("Active Price Subscriptions: " + str(active_price_subscriptions))
    if pair_address not in active_price_subscriptions:
        logger.info(f"Starting backend subscription for {pair_address}")
        # Create bridge callback
        handler = create_price_handler(pair_address)
        if ws_client_token_price:
            success = await ws_client_token_price.subscribe_token_price(
                token=pair_address, callback=handler)
            if success:
                active_price_subscriptions.add(pair_address)
            else:
                logger.error(f"Failed to subscribe backend for {pair_address}")

active_price_subscriptions = set()

@sio.on('unsubscribe_price')
async def on_unsubscribe_price(sid, pair_address: str):
    """Handle client unsubscription from token price."""
    room_name = f"price_{pair_address}"
    logger.info(f"Unsubscribing {sid} from {room_name}")
    await sio.leave_room(sid, room_name)
    
    try:
        # Check if room is empty
        # get_participants returns an iterator/list of SIDs
        participants = sio.manager.get_participants(namespace='/', room=room_name)
        # Convert to list to check length if it's an iterator, or just check truthiness if it returns None/empty
        # Re-using set/list logic for safety
        participant_count = 0
        try:
            participant_count = len(list(participants))
        except:
            pass
             
        logger.info(f"Room {room_name} members after leave: {participant_count}")
        
        if participant_count == 0:
            # Room is empty
            if pair_address in active_price_subscriptions:
                logger.info(f"No listeners for {pair_address}, unsubscribing backend")
                if ws_client_token_price:
                    await ws_client_token_price.unsubscribe_token_price(pair_address)
                active_price_subscriptions.discard(pair_address)
    except Exception as e:
        logger.warning(f"Error checking room state: {e}")

# bridge_callback imported from shared utils

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    global ws_client, ws_client_sol_price, ws_client_token_price, bg_task, bg_task_sol_price, bg_task_token_price
    
    # Setup Pulse tracker callbacks
    tracker.on_update = bridge_callback(on_token_update)
    tracker.on_new_token = bridge_callback(on_new_token)
    tracker.on_token_removed = bridge_callback(on_token_removed)
    
    # Pulse WebSocket subscription
    async def do_subscribe_pulse(client: AxiomTradeWebSocketClient):
        return await client.subscribe_to_pulse(
            filters=DEFAULT_PULSE_FILTERS,
            data_callback=tracker.process_message
        )

    async def run_pulse_connection():
        global ws_client, axiom_client
        logger.info("Starting Pulse WebSocket connection...")
        success, ws_client, axiom_client = await connect_with_retry(do_subscribe_pulse)
        if success:
            logger.info("Pulse connected!")
            await ws_client.ensure_connection_and_listen()
        else:
            logger.error("Pulse connection failed.")
    
    # SOL Price WebSocket subscription
    async def do_subscribe_sol_price(client: AxiomTradeWebSocketClient):
        return await client.subscribe_sol_price(
            callback=on_sol_price_update
        )
    
    async def run_sol_price_connection():
        global ws_client_sol_price
        logger.info("Starting SOL Price WebSocket connection...")
        success, ws_client_sol_price, axiom_client = await connect_with_retry(do_subscribe_sol_price)
        if success:
            logger.info("SOL Price connected!")
            await ws_client_sol_price.ensure_connection_and_listen()
        else:
            logger.error("SOL Price connection failed.")

    # Token Price WebSocket subscription
    async def run_token_price_connection():
        global ws_client_token_price
        logger.info("Starting Token Price WebSocket connection...")
        
        # Helper to ensure correct mode and just connect
        async def do_connect_token_price(client):
             return await client.connect(mode=WebSocketMode.TOKEN_PRICE)

        success, ws_client_token_price, _ = await connect_with_retry(do_connect_token_price)
        if success:
            logger.info("Token Price WebSocket connected!")
            await ws_client_token_price.ensure_connection_and_listen()
        else:
             logger.error("Token Price connection failed.")

    # Start all background tasks
    bg_task = asyncio.create_task(run_pulse_connection())
    bg_task_sol_price = asyncio.create_task(run_sol_price_connection())
    bg_task_token_price = asyncio.create_task(run_token_price_connection())
    
    yield
    
    # Cleanup on shutdown
    if bg_task:
        bg_task.cancel()
    if bg_task_sol_price:
        bg_task_sol_price.cancel()
    if bg_task_token_price:
        bg_task_token_price.cancel()
    if ws_client and ws_client.ws:
        await ws_client.ws.close()
    if ws_client_sol_price and ws_client_sol_price.ws:
        await ws_client_sol_price.ws.close()
    if ws_client_token_price and ws_client_token_price.ws:
        await ws_client_token_price.ws.close()

fastapi_app = FastAPI(lifespan=lifespan)
fastapi_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

@fastapi_app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "tokens": len(tracker.tokens)}

@fastapi_app.get("/api/tokens")
def get_tokens():
    """Get all tokens."""
    return [serialize_token(t) for t in tracker.get_all_tokens()]

@fastapi_app.get("/api/tokens/{pair_address}")
def get_token(pair_address: str):
    """Get single token by pair address."""
    token = tracker.tokens.get(pair_address)
    if not token:
        return {"error": "Token not found"}
    return serialize_token(token)

@fastapi_app.get("/api/candles/{pair_address}")
def get_candles(pair_address: str):
    """Get candles for a pair (proxies via backend)."""
    if not axiom_client:
        return {"error": "Backend client not ready"}
    
    try:
        # 1. Get metadata needed for chart request
        # We need: openTrading, pairCreatedAt (from pair-info), lastTransactionTime (from last-transaction), v (version/ts)
        
        # Parallel fetch if we were async, but client is sync for now or we wrap it?
        # The client methods are sync (requests based).
        
        pair_info = axiom_client.get_pair_info(pair_address)
        tx_data = axiom_client.get_last_transaction(pair_address)
        
        # 2. Extract parameters
        # Helper to parse ISO string to ms timestamp
        def to_ms(val):
            if isinstance(val, int): return val
            if isinstance(val, str):
                try:
                    # Parse ISO string
                    dt = date_parser.parse(val)
                    return int(dt.timestamp() * 1000)
                except:
                    return None
            return None

        open_trading_raw = pair_info.get("openTrading")
        pair_created_at_raw = pair_info.get("createdAt")
        last_tx_time_raw = tx_data.get("createdAt")
        
        open_trading = to_ms(open_trading_raw)
        pair_created_at = to_ms(pair_created_at_raw)
        last_tx_time = to_ms(last_tx_time_raw)

        # v: Use 'v' from tx_data or current time
        v = tx_data.get("v") or int(datetime.now().timestamp() * 1000)

        # 3. Calculate timestamps for 'from' and 'to'
        # User requested 30 minutes window
        to_ts = int(datetime.now().timestamp() * 1000)
        from_ts = to_ts - (30 * 60 * 1000) # 30 minutes
        
        # 4. Fetch candles
        candles = axiom_client.get_pair_chart(
            pair_address=pair_address,
            from_ts=from_ts,
            to_ts=to_ts,
            open_trading=open_trading,
            pair_created_at=pair_created_at,
            last_transaction_time=last_tx_time,
            currency="USD",
            interval="1s",
            count_bars=2000,
            v=v
        )
        
        # 5. Extract token info for frontend
        total_supply = float(pair_info.get("supply") or pair_info.get("totalSupply") or 1_000_000_000)
        
        return {
            "candles": candles,
            "token_info": {
                "total_supply": total_supply,
                "created_at": pair_created_at_raw
            }
        }
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        return {"error": str(e)}

# --- Bot State Endpoint ---
@fastapi_app.post("/api/bot/state")
async def update_bot_state(state: BotState):
    """Receive update from the trading bot and broadcast it."""
    # Broadcast to all connected clients
    await sio.emit('bot_state_update', state.model_dump())
    return {"status": "ok"}

@sio.event
async def disconnect(sid):
    """Handle socket disconnection."""
    logger.info(f"Disconnected: {sid}")
    
    # Check all active subscriptions to see if any rooms became empty
    # We must iterate over a copy since we might modify the set
    for pair_address in list(active_price_subscriptions):
        room_name = f"price_{pair_address}"
        try:
            participants = sio.manager.get_participants(namespace='/', room=room_name)
            
            # Check if any participants remain
            has_participants = False
            try:
                # Try to get at least one item
                next(participants)
                has_participants = True
            except StopIteration:
                pass
                
            if not has_participants:
                logger.info(f"Room {room_name} empty after disconnect, unsubscribing backend")
                if ws_client_token_price:
                    await ws_client_token_price.unsubscribe_token_price(pair_address)
                active_price_subscriptions.discard(pair_address)
                
        except Exception as e:
            logger.warning(f"Error checking {room_name} on disconnect: {e}")

@sio.event
async def connect(sid, environ):
    """Handle new socket connection."""
    logger.info(f"Connected: {sid}")
    
    # Send snapshot of all tokens
    tokens = [serialize_token(t) for t in tracker.get_all_tokens()]
    tokens.sort(key=lambda x: x.get('created_at', '') or '', reverse=True)
    await sio.emit('snapshot', tokens, to=sid)
    
    # Send current SOL price if available
    if current_sol_price is not None:
        await sio.emit('sol_price', {
            'price': current_sol_price,
            'timestamp': datetime.utcnow().isoformat()
        }, to=sid)

@sio.on('request_snapshot')
async def on_request_snapshot(sid):
    """Handle client request for snapshot."""
    logger.info(f"Snapshot requested by: {sid}")
    tokens = [serialize_token(t) for t in tracker.get_all_tokens()]
    tokens.sort(key=lambda x: x.get('created_at', '') or '', reverse=True)
    await sio.emit('snapshot', tokens, to=sid)
    
    if current_sol_price is not None:
        await sio.emit('sol_price', {
            'price': current_sol_price,
            'timestamp': datetime.utcnow().isoformat()
        }, to=sid)

if __name__ == "__main__":
    uvicorn.run("src.pulse_dashboard.server.api:app", host="0.0.0.0", port=8000, reload=True)
