class BaseUrls:
    API_MAIN = "https://api.axiom.trade"
    API_V2 = "https://api2.axiom.trade"
    API_V3 = "https://api3.axiom.trade"
    API_V4 = "https://api4.axiom.trade"
    API_V5 = "https://api5.axiom.trade"
    API_V6 = "https://api6.axiom.trade"
    API_V7 = "https://api7.axiom.trade"
    API_V8 = "https://api8.axiom.trade"
    API_V9 = "https://api9.axiom.trade"
    API_V10 = "https://api10.axiom.trade"
    PUMP_PORTAL = "https://pumpportal.fun/api"
    AXIOM_TRADE = "https://axiom.trade"

class Endpoints:
    # Base Urls
    BASE_URL_API = f"{BaseUrls.AXIOM_TRADE}/api"
    BASE_URL = BaseUrls.AXIOM_TRADE
    BASE_URL_API_MAIN = f"{BaseUrls.API_MAIN}"
    # Auth
    LOGIN_PASSWORD = f"{BaseUrls.API_V6}/login-password-v2"
    LOGIN_OTP = f"{BaseUrls.API_V10}/login-otp"
    REFRESH_TOKEN = f"{BaseUrls.API_V9}/refresh-access-token"
    USER_INFO = f"{BaseUrls.API_MAIN}/user/info" # Assuming main based on urls.py usage pattern or just path, but urls.py didn't specify base for user info clearly, defaulting to MAIN or just path if needed. *Correction*: client.py didn't use user info hardcoded, but urls.py had it. Let's include it.

    # Token/Market Data
    TRENDING_MEME = f"{BaseUrls.API_V6}/meme-trending-v2"
    TOKEN_DETAILS = f"{BaseUrls.API_V6}/token" # /{token_address}
    PORTFOLIO = f"{BaseUrls.API_V6}/portfolio"
    
    TOKEN_INFO = f"{BaseUrls.API_V2}/token-info"
    LAST_TRANSACTION = f"{BaseUrls.API_V2}/last-transaction"
    PAIR_INFO = f"{BaseUrls.API_V2}/pair-info"
    PAIR_STATS = f"{BaseUrls.API_V2}/pair-stats"
    MEME_OPEN_POSITIONS = f"{BaseUrls.API_V2}/meme-open-positions"
    HOLDER_DATA = f"{BaseUrls.API_V2}/holder-data-v5"
    DEV_TOKENS = f"{BaseUrls.API_V2}/dev-tokens-v3"
    TOKEN_ANALYSIS = f"{BaseUrls.API_V2}/token-analysis"
    PAIR_CHART = f"{BaseUrls.API_V2}/pair-chart-v2"
    MARKET_LIGHTHOUSE = f"{BaseUrls.API_V2}/lighthouse"

    # Trading
    TRADE_LOCAL = f"{BaseUrls.PUMP_PORTAL}/trade-local"
    
    ENDPOINT_GET_BALANCE = f"{BASE_URL_API}/sol-balance"
    ENDPOINT_GET_BATCHED_BALANCE = f"{BASE_URL_API_MAIN}/batched-sol-balance-v2"
    ENDPOINT_BUY_TOKEN = f"{BASE_URL_API}/buy"
    ENDPOINT_SELL_TOKEN = f"{BASE_URL_API}/sell"
    ENDPOINT_SEND_TRANSACTION = f"{BASE_URL_API}/send-transaction"
    ENDPOINT_GET_TOKEN_BALANCE = f"{BASE_URL_API}/token-balance"

class Websockets:
    MAIN = "wss://cluster6.axiom.trade/"
    TOKEN_PRICE = "wss://socket8.axiom.trade/"
    CLUSTER_3 = "wss://cluster3.axiom.trade/"
    PULSE = "wss://pulse2.axiom.trade/ws"