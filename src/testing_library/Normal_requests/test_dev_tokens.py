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
    # Developer address to investigate
    dev_address = "38xYCF1J1FtY9AbtWVZPSQFDVj7k7E6p9oXTXdUZyK4d"

    # Get all tokens created by this developer
    result = client.get_dev_tokens(dev_address)

    print(f"📊 Developer Token Analysis")
    print(f"=" * 50)
    print(f"Total tokens: {result['counts']['totalCount']} :")
    # print(f"Active tokens: {result['counts']['active']}")
    # print(f"Rugged tokens: {result['counts']['rugged']}")
    # print(f"Failed launches: {result['counts']['failed']}")
    print(result['tokens'][0])
except Exception as e:
    raise Exception(f"❌ Error: {e}")
# print(f"\n📈 Statistics:")
# print(f"Success rate: {result['statistics']['successRate']:.1f}%")
# print(f"Avg liquidity: {result['statistics']['averageInitialLiquidity']:.2f} SOL")