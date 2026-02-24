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
    pair_address = "Cqs5ErFv4sfaGDpgvxxHSPeshb1sKNFy4zyB5R5kQjj3"

    # Get last transaction
    last_tx = client.get_last_transaction(pair_address)
    print(last_tx)

    print(f"Last transaction: {last_tx['type']}")
    print(f"Price: ${last_tx['priceUsd']:.8f}")
    print(f"Amount: {last_tx['tokenAmount']:,.0f} tokens")
    print(f"Total Value: ${last_tx['totalUsd']:.2f}")
    print(f"Timestamp: {last_tx['createdAt']}")
except Exception as e:
    raise Exception(f"❌ Error: {e}")