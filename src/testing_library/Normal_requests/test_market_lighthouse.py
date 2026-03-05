import os
from dotenv import load_dotenv

from axiomtradeapi import AxiomTradeClient

# Load environment variables
load_dotenv()

# Initialize the client
client = AxiomTradeClient(
    auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
    refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
)

try:
    # Get last transaction
    info = client.get_market_weather()

    print(info)
except Exception as e:
    raise Exception(f"❌ Error: {e}")