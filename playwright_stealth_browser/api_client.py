"""
Stealth API Client executing REST requests natively in a Playwright browser context.

This client replaces standard `requests`/`urllib3` calls to bypass Cloudflare
(526/418 errors) by evaluating native `fetch()` Javascript commands directly 
in the authenticated Chromium tab maintained by BrowserPulseProvider.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from .api_templates import ApiTemplates
from .endpoints import Endpoints

logger = logging.getLogger(__name__)

class StealthApiClient:
    """ API Client executing REST requests natively in a Playwright browser context. """
    def __init__(self, provider: Any):
        """
        Initialize with the BrowserPulseProvider instance.
        The provider handles thread-safe Javascript execution routing to the background Chromium thread.
        """
        self.provider = provider

    def execute_js(self, js_code: str) -> Dict[str, Any]:
        """
        Execute an arbitrary javascript fetch block inside the Chromium page context.
        """
        try:
            # Route execution to the thread-safe provider queue
            result = self.provider.evaluate_js(js_code)
            
            # Check for fetch level failures we bubbled up
            if isinstance(result, dict) and "error" in result:
                logger.error(f"Stealth API Fetch Error: HTTP {result.get('error')} | {result.get('text', '')}")
                return None
            return result
        except Exception as e:
            logger.error(f"Failed to execute fetch in stealth browser context: {e}")
            return None

    def get_full_token_analysis(self, pair_address: str) -> Optional[Dict]:
        
        requests_js = f"""
            async () => {{
                const fetchWithCredentials = async (url) => {{
                    try {{
                        const resp = await fetch(url, {{ credentials: 'include' }});
                        if (!resp.ok) return {{ error: resp.status, text: await resp.text() }};
                        return await resp.json();
                    }} catch (e) {{
                        return {{ error: e.message }};
                    }}
                }};
                
                const pairAddress = "{pair_address}";
                
                // process a single token's endpoints
                // Step 1: Fire TX and Info parallel
                const [txData, pairInfo] = await Promise.all([
                    fetchWithCredentials(`{Endpoints.LAST_TRANSACTION}?pairAddress=${{pairAddress}}`),
                    fetchWithCredentials(`{Endpoints.PAIR_INFO}?pairAddress=${{pairAddress}}`)
                ]);
                
                // Step 2: Extract timestamps safely and calculate chart query timeframe
                const nowMs = Date.now();
                const fromTs = nowMs - (45 * 60 * 1000);
                
                const getMs = (val) => val ? new Date(val).getTime() : 0;
                const openTrading = getMs(pairInfo?.openTrading);
                const pairCreatedAt = getMs(pairInfo?.createdAt);
                const lastTxTime = getMs(txData?.createdAt);
                const v = txData?.v || nowMs;
                
                const chartUrl = `{Endpoints.PAIR_CHART}?pairAddress=${{pairAddress}}&from=${{fromTs}}&to=${{nowMs}}&currency=USD&interval=1m&openTrading=${{openTrading}}&pairCreatedAt=${{pairCreatedAt}}&lastTransactionTime=${{lastTxTime}}&countBars=500&showOutliers=false&isNew=false&v=${{v}}`;
                
                // Step 3: Fire Chart and Holders parallel
                const [chartData, holderData] = await Promise.all([
                    fetchWithCredentials(chartUrl),
                    fetchWithCredentials(`{Endpoints.HOLDER_DATA}?pairAddress=${{pairAddress}}&onlyTrackedWallets=false`)
                ]);
                
                return {{
                    chart_data: chartData,
                    holder_data: holderData
                }};
            }}
        """

        try:
            result = self.provider.evaluate_js(requests_js)
            if isinstance(result, dict):
                for key in ['chart_data', 'holder_data']:
                    data = result.get(key)
                    if isinstance(data, dict) and 'error' in data:
                        logger.error("Stealth API Fetch Error in %s for %s: HTTP %s | %s", key, pair_address, data.get('error'), data.get('text', ''))
            return result
        except Exception as e:
            logger.error(f"Failed to execute native JS requests for getting single token: {e}")
            return None

        
    def get_full_token_analysis_batch(self, tokens: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Highest performance orchestration method.
        Takes a list of N pair addresses and runs `get_last_transaction`, 
        `get_pair_info`, `get_pair_chart`, and `get_holder_data` for ALL of them natively
        inside Chromium using Promise.all mapping.
        
        Returns a dictionary mapping:
        { "pair_abc": { "tx_data": {...}, "pair_info": {...}, "chart_data": {...}, "holder_data": {...} } }
        """
        # Convert python list to javascript array
        tokens_js_array = str(tokens).replace("'", '"')
        
        orchestration_js = f"""
            async () => {{
                const fetchWithCredentials = async (url) => {{
                    try {{
                        const resp = await fetch(url, {{ credentials: 'include' }});
                        if (!resp.ok) return {{ error: resp.status, text: await resp.text() }};
                        return await resp.json();
                    }} catch (e) {{
                        return {{ error: e.message }};
                    }}
                }};
                
                const tokens = {tokens_js_array};
                const BATCH_SIZE = 1; // Number of tokens to process concurrently to avoid rate limits
                const results = [];
                
                // Helper function to process a single token's endpoints
                const processToken = async (pairAddress) => {{
                    // Step 1: Fire TX and Info parallel
                    const [txData, pairInfo] = await Promise.all([
                        fetchWithCredentials(`{Endpoints.LAST_TRANSACTION}?pairAddress=${{pairAddress}}`),
                        fetchWithCredentials(`{Endpoints.PAIR_INFO}?pairAddress=${{pairAddress}}`)
                    ]);
                    
                    // Step 2: Extract timestamps safely and calculate chart query timeframe
                    const nowMs = Date.now();
                    const fromTs = nowMs - (30 * 60 * 1000);
                    
                    const getMs = (val) => val ? new Date(val).getTime() : 0;
                    const openTrading = getMs(pairInfo?.openTrading);
                    const pairCreatedAt = getMs(pairInfo?.createdAt);
                    const lastTxTime = getMs(txData?.createdAt);
                    const v = txData?.v || nowMs;
                    
                    const chartUrl = `{Endpoints.PAIR_CHART}?pairAddress=${{pairAddress}}&from=${{fromTs}}&to=${{nowMs}}&currency=USD&interval=1m&openTrading=${{openTrading}}&pairCreatedAt=${{pairCreatedAt}}&lastTransactionTime=${{lastTxTime}}&countBars=500&showOutliers=false&isNew=false&v=${{v}}`;
                    
                    // Step 3: Fire Chart and Holders parallel
                    const [chartData, holderData] = await Promise.all([
                        fetchWithCredentials(chartUrl),
                        fetchWithCredentials(`{Endpoints.HOLDER_DATA}?pairAddress=${{pairAddress}}&onlyTrackedWallets=false`)
                    ]);
                    
                    return {{
                        pair_address: pairAddress,
                        tx_data: txData,
                        pair_info: pairInfo,
                        chart_data: chartData,
                        holder_data: holderData
                    }};
                }};

                // Orchestrate tokens in chunks to respect rate limits
                for (let i = 0; i < tokens.length; i += BATCH_SIZE) {{
                    const batchTokens = tokens.slice(i, i + BATCH_SIZE);
                    // Process this chunk concurrently
                    const batchPromises = batchTokens.map(processToken);
                    const batchResults = await Promise.all(batchPromises);
                    results.push(...batchResults);
                    
                    // Delay between batches to stay under rate limits (500ms is safer than 200ms)
                    //if (i + BATCH_SIZE < tokens.length) {{
                    //    await new Promise(r => setTimeout(r, 100));
                    //}}
                }}
                
                // Package into Python-parseable dict natively
                const outputMap = {{}};
                for (const res of results) {{
                    outputMap[res.pair_address] = res;
                }}
                return outputMap;
            }}
        """
        
        try:
            return self.provider.evaluate_js(orchestration_js)
        except Exception as e:
            logger.error(f"Failed to execute native JS orchestration batch: {e}")
            return {}

    
        
    # --- Market Data Endpoints --- 

    def get_token_info(self, pair_address: str) -> Optional[Dict]:
        js = ApiTemplates.get_token_info(pair_address)
        return self.execute_js(js)

    def get_pair_info(self, pair_address: str) -> Optional[Dict]:
        js = ApiTemplates.get_pair_info(pair_address)
        return self.execute_js(js)

    def get_market_lighthouse(self) -> Optional[Dict]:
        js = ApiTemplates.get_market_lighthouse()
        return self.execute_js(js)

    def get_last_transaction(self, pair_address: str) -> Optional[Dict]:
        js = ApiTemplates.get_last_transaction(pair_address)
        return self.execute_js(js)

    def get_holder_data(self, pair_address: str, only_tracked: bool = False) -> Optional[Dict]:
        js = ApiTemplates.get_holder_data(pair_address, only_tracked)
        return self.execute_js(js)

    def get_dev_tokens(self, dev_address: str) -> Optional[Dict]:
        js = ApiTemplates.get_dev_tokens(dev_address)
        return self.execute_js(js)

    def get_pair_chart(self,
                    pair_address: str,
                    from_ts: int,
                    to_ts: int,
                    open_trading: int,
                    pair_created_at: int,
                    last_transaction_time: int,
                    currency: str = "USD",
                    interval: str = "1s",
                    count_bars: int = 300,
                    show_outliers: bool = False,
                    is_new: bool = False,
                    v: int = None) -> Optional[Dict]:
        js = ApiTemplates.get_pair_chart(pair_address, from_ts, to_ts, open_trading, pair_created_at, last_transaction_time, currency, interval, count_bars, show_outliers, is_new, v)
        return self.execute_js(js)
        
    def get_meme_trending(self, time_period: str = '1h') -> Optional[Dict]:
        js = ApiTemplates.get_meme_trending(time_period)
        return self.execute_js(js)

    # --- Wallet / Balance Endpoints ---

    def get_batched_sol_balance(self, wallet_addresses: List[str]) -> Dict[str, float]:
        js = ApiTemplates.get_batched_balance(wallet_addresses)
        result = self.execute_js(js)
        parsed_results = {}
        
        if result and isinstance(result, dict):
            for addr, val in result.items():
                if isinstance(val, dict):
                    sol_val = val.get('solBalance') or val.get('sol') or val.get('balance')
                    if sol_val is not None:
                        parsed_results[addr] = float(sol_val)
        return parsed_results

    def get_sol_balance(self, wallet_address: str) -> Optional[float]:
        results = self.get_batched_sol_balance([wallet_address])
        return results.get(wallet_address)
