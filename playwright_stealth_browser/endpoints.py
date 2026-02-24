class BaseUrls:
    BASE = "https://axiom.trade"

class Endpoints:
    BASE_URL = BaseUrls.BASE
    PULSE = f"{BASE_URL}/pulse"
    
class Websockets:
    PULSE = "wss://pulse2.axiom.trade/ws"
    MAIN = "wss://cluster9.axiom.trade/"
    TOKEN_PRICE = "wss://socket8.axiom.trade/"