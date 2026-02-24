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

# Query any Solana wallet balance
wallet_address = "3xJbAVun5TubvK43w8HYP29kapfXxJGg8HEsRBT7B7XA"

print(f"🔄 Fetching balance for: {wallet_address}")

try:
    # Use the client method directly
    balance = client.get_sol_balance(wallet_address)
    
    if balance is not None:
        print(f"✅ Success! Balance: {balance} SOL")
        print(f"   Lamports: {int(balance * 1_000_000_000)}")
    else:
        raise Exception("❌ Failed to get balance")

except Exception as e:
    raise Exception(f"❌ Error: {e}")