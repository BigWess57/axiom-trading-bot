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
    address = "9EL7ZxBPqtakgA3aHSMX3hDEXy1Y5BKupotjiRW9icQz"

    # Get last transaction
    info = client.get_token_info_by_pair(address)

    print(info)
except Exception as e:
    raise Exception(f"❌ Error: {e}")

# print(f"Last transaction: {last_tx['type']}")
# print(f"Price: ${last_tx['priceUsd']:.8f}")
# print(f"Amount: {last_tx['tokenAmount']:,.0f} tokens")
# print(f"Total Value: ${last_tx['totalUsd']:.2f}")
# print(f"Timestamp: {last_tx['createdAt']}")