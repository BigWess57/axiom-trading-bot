# Plan to Fix Axiom Library

The library `axiomtradeapi` installed in your environment is outdated. Since the API has changed (e.g., `sol-balance` is gone, `batched-sol-balance` is needed), we need to update the client code.

Since we cannot easily patch `pip` installed packages persistently, the best approach is to **vendor** the library (copy it into your project) and fix it there.

## Steps

1.  **Vendor the Library**
    *   Copy the `axiomtradeapi` source code from your virtual environment into your project root.
    *   This ensures your changes are saved in git and take precedence over the installed package.

2.  **Implement Batched Balance**
    *   File: `axiomtradeapi/client.py`
    *   Action: Add a new method `get_batched_sol_balance` that accepts a list of public keys and hits the `/batched-sol-balance` endpoint.

3.  **Fix Legacy functions**
    *   File: `axiomtradeapi/client.py`
    *   Action: Update `get_sol_balance` to internally use `get_batched_sol_balance([wallet_address])`. This fixes the broken function without breaking existing code that calls it.

4.  **Fix WebSocket Client**
    *   File: `axiomtradeapi/websocket/_client.py`
    *   Action: Update `websockets.connect` to use `additional_headers` for compatibility.
    *   Action: Fix `_message_handler` to correctly parse token data for callbacks.
    *   Action: Ensure tokens are refreshed automatically on 401 connection errors.

5.  **Verify**
    *   Run `test_custom_balance.py` to confirm REST API fixes.
    *   Run `Basic_websocket_connection.py` to confirm WebSocket connectivity and automatic token refresh/persistence.
