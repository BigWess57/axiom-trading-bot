# Changes Summary for AxiomTradeAPI

This document summarizes the changes made to the `axiomtradeapi` library to fix compatibility issues with the latest Axiom API endpoints and Python dependencies.

## Key Changes

### 1. WebSocket Client Fixes & Improvements

*   **Fixed `websockets` Library Compatibility**: 
    *   Updated `axiomtradeapi/websocket/_client.py` to use `additional_headers` instead of `extra_headers` in the `websockets.connect()` call. This fixes a crash with `websockets` version 14.0+.
*   **Updated WebSocket Endpoints**:
    *   Changed default WebSocket URL to `wss://cluster6.axiom.trade/` to match current API infrastructure.
*   **Exposed WebSocket Client**:
    *   Added `AxiomTradeWebSocketClient` to `axiomtradeapi/__init__.py` so it can be directly imported.
    *   Added `get_websocket_client()` helper method to `AxiomTradeClient` in `axiomtradeapi/client.py` for easier instantiation using existing authentication.
*   **Fixed Authentication & Token Handling**:
    *   Resolved cookie-based authentication for WebSocket connections.
    *   **Automatic Token Refresh Mechanism**: Implemented a robust connection flow that detects `401 Unauthorized` errors (typically caused by expired tokens). If a connection fails, the client should call `client.refresh_access_token()` to fetch new tokens from the API and then retry the connection.
    *   **Handling Token Expiration**: Unlike REST requests which refresh tokens transparently, WebSocket connections require valid tokens at the moment of the handshake. By calling the refresh function on failure, the script ensures that the connection can be established even after the initial `.env` tokens have expired.
    *   **Note**: Browser DevTools doesn't display cookies in WebSocket headers for security, but they ARE required and sent automatically by browsers. The Python client explicitly sends `Cookie` headers with `auth-access-token` and `auth-refresh-token` to mimic this behavior.
*   **Fixed Message Parsing**:
    *   Updated `_message_handler` in `axiomtradeapi/websocket/_client.py` to correctly extract the `content` field from new token messages and wrap it in an array before passing to callbacks.
    *   This fixes the `'str' object has no attribute 'get'` error that occurred when the callback received the full message dict instead of the token content.

**Example File Enhancements** (`testing_library/Websocket/Basic_websocket_connection.py`):
*   **Automatic Token Refresh**: Added retry logic that automatically calls `client.refresh_access_token()` if the WebSocket connection fails on the first attempt.
*   **Token Persistence**: Automatically saves refreshed tokens back to the `.env` file using `python-dotenv`'s `set_key()` function, ensuring tokens remain valid across script restarts.
*   **User-Friendly Error Messages**: Provides clear guidance when automatic refresh fails, instructing users to copy fresh tokens from browser cookies.
*   **Configurable Retries**: Supports up to 2 connection attempts with automatic token refresh between failures.

### 2. SOL Balance Endpoint Update

*   **Implemented Batched Balance**:
    *   Added `get_batched_sol_balance(wallet_addresses)` method to `AxiomTradeClient`.
    *   Uses the new `/batched-sol-balance` endpoint instead of the deprecated `/sol-balance`.
    *   Implemented robust parsing to handle various response formats (list vs dict) and key names (`sol`, `solBalance`, `balance`).
*   **Restored Backward Compatibility**:
    *   Refactored the existing `get_sol_balance(wallet_address)` method to internally call `get_batched_sol_balance`. 
    *   This ensures existing code using `get_sol_balance` continues to work without modification, resolving the 404/405 errors from the dead endpoint.

## Files Modified

*   `axiomtradeapi/client.py`: Added batched balance methods, updated WebSocket helper.
*   `axiomtradeapi/websocket/_client.py`: Fixed connection arguments, URLs, and auth headers.
*   `axiomtradeapi/__init__.py`: Exported WebSocket client.

## Verification

*   **REST API**: Confirmed `get_sol_balance` now works correctly using the batched endpoint.
*   **WebSocket**: Verified connection attempts to new URLs (though server-side auth restrictions may still apply depending on token permissions).

### 3. Endpoint Management Refactoring

*   **Information about `get_token_info` and  `get_user_portfolio`method**:
    *   Added comment saying that these 2 functions are not working and need to be updated.

*   **Consolidated Endpoint Definitions**:
    *   Moved all API URL definitions to `axiomtradeapi/content/endpoints.py`.
    *   Created `BaseUrls` class to manage different API subdomains (api, api2...api10).
    *   Created `Websockets` class to centralization WebSocket URLs.
    *   Updated `Endpoints` class to use `BaseUrls` constants, facilitating easier updates and maintenance.
    *   Deleted `axiomtradeapi/urls.py` as it is now redundant.

*   **Codebase Standardization**:
    *   Updated `axiomtradeapi/client.py`, `axiomtradeapi/websocket/_client.py`, `axiomtradeapi/auth/login.py`, and `axiomtradeapi/auth/auth_manager.py` to use the centralized `Endpoints` constants instead of hardcoded URL strings.
    *   Updated `axiomtradeapi/helpers/TryServers.py` to dynamically check servers using the new `BaseUrls` class.

*   **Improved Testing**:
    *   Updated tests in `src/testing_library/Normal_requests/` to wrap API calls in `try...except` blocks and explicitly raise exceptions on failure. This ensures that test runners correctly identify failed API calls as test failures.

### 4. Codebase Refactoring & Pulse Integration

*   **Client Refactoring**:
    *   Split the massive `axiomtradeapi/client.py` into a modular package `axiomtradeapi/xhr_client/`.
    *   Functionality separated into Mixins: `AuthMixin`, `MarketDataMixin`, `TradingMixin`, `WalletMixin`.
    *   Renamed package from `client` to `xhr_client` for clarity.

*   **WebSocket Refactoring**:
    *   Refactored `axiomtradeapi/websocket/_client.py` into a clean package structure under `axiomtradeapi/websocket/`.
    *   Separated concerns into `connection.py`, `subscription.py`, `handler.py`, and `types.py`.
    *   Fixed Method Resolution Order (MRO) issues to ensure correct mixin inheritance.

*   **Pulse WebSocket Features**:
    *   Added `subscribe_to_pulse(filters)` method to support real-time Pulse dashboard data.
    *   Implemented binary message handling (MessagePack) in `handler.py`.
    *   Added message counting for binary Pulse messages to track data throughput.
