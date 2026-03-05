"""
JavaScript templates for making API requests natively from within the stealth browser.
These templates utilize the modern fetch API and are executed via Playwright's `page.evaluate()`.

Parameters should be formatted into the strings before evaluation.
"""

from .endpoints import Endpoints

def _wrap_fetch(url: str, options_js: str = "{ method: 'GET' }") -> str:
    """Helper to wrap fetch logic with error handling and strictly enforce cross-origin cookies."""
    return f"""
        async () => {{
            try {{
                const opts = {{ ...{options_js}, credentials: 'include' }};
                const resp = await fetch('{url}', opts);
                if (!resp.ok) return {{ error: resp.status, text: await resp.text() }};
                return await resp.json();
            }} catch(e) {{
                return {{ error: e.message }};
            }}
        }}
    """

class ApiTemplates:
    
    @staticmethod
    def get_batched_balance(wallets: list[str]) -> str:
        # Convert python list to JS array string
        wallets_js = str(wallets).replace("'", '"')
        options = f"""{{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }},
            body: JSON.stringify({{ publicKeys: {wallets_js} }})
        }}"""
        return _wrap_fetch(Endpoints.ENDPOINT_GET_BATCHED_BALANCE, options)

    @staticmethod
    def get_pair_info(pair_address: str) -> str:
        url = f"{Endpoints.PAIR_INFO}?pairAddress={pair_address}"
        return _wrap_fetch(url)

    @staticmethod
    def get_token_info(pair_address: str) -> str:
        url = f"{Endpoints.TOKEN_INFO}?pairAddress={pair_address}"
        return _wrap_fetch(url)
        
    @staticmethod
    def get_market_lighthouse() -> str:
        return _wrap_fetch(Endpoints.MARKET_LIGHTHOUSE)

    @staticmethod
    def get_last_transaction(pair_address: str) -> str:
        url = f"{Endpoints.LAST_TRANSACTION}?pairAddress={pair_address}"
        return _wrap_fetch(url)

    @staticmethod
    def get_holder_data(pair_address: str, only_tracked: bool = False) -> str:
        tracked = "true" if only_tracked else "false"
        url = f"{Endpoints.HOLDER_DATA}?pairAddress={pair_address}&onlyTrackedWallets={tracked}"
        return _wrap_fetch(url)

    @staticmethod
    def get_dev_tokens(dev_address: str) -> str:
        url = f"{Endpoints.DEV_TOKENS}?devAddress={dev_address}"
        return _wrap_fetch(url)

    @staticmethod
    def get_pair_chart(pair_address: str, from_ts: int, to_ts: int, open_trading: int, pair_created_at: int, last_transaction_time: int, currency: str = "USD", interval: str = "1s", count_bars: int = 300, show_outliers: bool = False, is_new: bool = False, v: int = None) -> str:
        if v is None:
            v = to_ts
        outliers = "true" if show_outliers else "false"
        new = "true" if is_new else "false"
        url = f"{Endpoints.PAIR_CHART}?pairAddress={pair_address}&from={from_ts}&to={to_ts}&currency={currency}&interval={interval}&openTrading={open_trading}&pairCreatedAt={pair_created_at}&lastTransactionTime={last_transaction_time}&countBars={count_bars}&showOutliers={outliers}&isNew={new}&v={v}"
        return _wrap_fetch(url)

    @staticmethod
    def get_meme_trending(time_period: str = "1h") -> str:
        url = f"{Endpoints.TRENDING_MEME}?timePeriod={time_period}"
        return _wrap_fetch(url)
