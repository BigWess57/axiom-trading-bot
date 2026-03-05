from playwright.sync_api import Page, expect
import sys
import os

# Make src importable from playwright_tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright_stealth_browser.api_client import StealthApiClient

# Default test pair (Pnuts / SOL)
TEST_PAIR_CHART = "JYkWtkVuPhcUGCX1aV4f9YatKAeE44559MgsGvuanoV"
TEST_PAIR_INFO = "DqVhzJnuNC5pjEKdwV3cEqsf3ThXPvzzaKMaki3vJ1p8"
TEST_TOKEN_INFO_BY_PAIR = "9EL7ZxBPqtakgA3aHSMX3hDEXy1Y5BKupotjiRW9icQz"
TEST_HOLDER_DATA = "2pQGrjdChonWdFpMkzKkLXzmF3WAMuHaLFV1hgEyK21q"
TEST_LAST_TRANSACTION = "Cqs5ErFv4sfaGDpgvxxHSPeshb1sKNFy4zyB5R5kQjj3"
TEST_DEV = "38xYCF1J1FtY9AbtWVZPSQFDVj7k7E6p9oXTXdUZyK4d"
TEST_WALLET = "3xJbAVun5TubvK43w8HYP29kapfXxJGg8HEsRBT7B7XA"


def setup_client(page: Page) -> StealthApiClient:
    """Helper to navigate and setup the client."""
    page.goto("https://axiom.trade/")
    page.wait_for_load_state("domcontentloaded")
    return StealthApiClient(page)


def test_get_token_info(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_token_info for {TEST_TOKEN_INFO_BY_PAIR}...")
    result = client.get_token_info(TEST_TOKEN_INFO_BY_PAIR)
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_pair_info(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_pair_info for {TEST_PAIR_INFO}...")
    result = client.get_pair_info(TEST_PAIR_INFO)
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_market_lighthouse(page: Page):
    client = setup_client(page)
    print("📡 Testing get_market_lighthouse...")
    result = client.get_market_lighthouse()
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_last_transaction(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_last_transaction for {TEST_LAST_TRANSACTION}...")
    result = client.get_last_transaction(TEST_LAST_TRANSACTION)
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_holder_data(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_holder_data for {TEST_HOLDER_DATA}...")
    result = client.get_holder_data(TEST_HOLDER_DATA, only_tracked=False)
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_dev_tokens(page: Page):
    client = setup_client(page)
    # Using the test wallet as a stand-in for creator address
    print(f"📡 Testing get_dev_tokens for {TEST_DEV}...")
    result = client.get_dev_tokens(TEST_DEV)
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_pair_chart(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_pair_chart for {TEST_PAIR_CHART}...")
    # Fetch latest 5m chart, using dummy timestamps for required positional args
    from datetime import datetime
    from dateutil import parser as date_parser

    # v: Use 'v' from tx_data or current time
    v = int(datetime.now().timestamp() * 1000)

    # 2. Calculate timestamps for 'from' and 'to' (30 mins)
    to_ts = int(datetime.now().timestamp() * 1000)
    from_ts = to_ts - (5 * 60 * 1000) # 30 minutes

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

    open_trading = to_ms("2026-03-04T16:10:10.386Z")
    pair_created_at = to_ms("2026-03-04T16:11:10.386Z")
    last_tx_time = to_ms("2026-03-04T16:15:29.038Z")

    result = client.get_pair_chart(
            pair_address=TEST_PAIR_CHART,
            from_ts=from_ts,
            to_ts=to_ts,
            open_trading=open_trading,
            pair_created_at=pair_created_at,
            last_transaction_time=last_tx_time,
            interval="1m",
            currency="USD",
            count_bars=500,
            show_outliers=False,
            is_new=False,
            v=v
        )
    print(f"✅ Result: {str(result)[:200]}...")
    assert result is not None
    assert "error" not in result

def test_get_meme_trending(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_meme_trending...")
    result = client.get_meme_trending(time_period="1h")
    print(f"✅ Result: {str(result)[:200]}")
    assert result is not None
    assert "error" not in result

def test_get_batched_sol_balance(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_batched_sol_balance for {TEST_WALLET}...")
    result = client.get_batched_sol_balance([TEST_WALLET])
    print(f"✅ Result: {result}")
    assert result is not None
    assert TEST_WALLET in result

def test_get_sol_balance(page: Page):
    client = setup_client(page)
    print(f"📡 Testing get_sol_balance for {TEST_WALLET}...")
    result = client.get_sol_balance(TEST_WALLET)
    print(f"✅ Result: {result}")
    assert result is not None
    assert isinstance(result, float)
