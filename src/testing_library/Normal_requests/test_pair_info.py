from axiomtradeapi import AxiomTradeClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client
client = AxiomTradeClient(
    auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
    refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
)

try:
    address = "DqVhzJnuNC5pjEKdwV3cEqsf3ThXPvzzaKMaki3vJ1p8"

    # Get last transaction
    info = client.get_pair_info(address)

    print(info)
except Exception as e:
    raise Exception(f"❌ Error: {e}")