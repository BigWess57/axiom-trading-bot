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
    pair_address = "2pQGrjdChonWdFpMkzKkLXzmF3WAMuHaLFV1hgEyK21q"

    # Get all holder data
    result = client.get_holder_data(pair_address, only_tracked_wallets=False)

    print(f"📊 Token Holder Analysis")
    # print(f"=" * 20)
    print(f"Total holders: {len(result)}")
    # print(result)
    print(f'Top 10 holders addresses: (not counting liquidity pool)')
    for holder in result[1:11]:
        print(holder[0])
    print(f'Top 10 holders sol balances:')
    for holder in result[1:11]:
        print(holder[2])
    print(f'Biggest holder: {result[1][0]} with {result[1][1]} tokens')
except Exception as e:
    raise Exception(f"❌ Error: {e}")
# print(f"Tracked wallets: {result['trackedWallets']}")
# print(f"Top 10 hold: {result['top10HoldingPercentage']:.1f}%")
# print(f"Top 20 hold: {result['top20HoldingPercentage']:.1f}%")

# print(f"\n🔒 Concentration Risk")
# print(f"Risk Level: {result['concentration']['concentrationRisk']}")
# print(f"Gini: {result['concentration']['giniCoefficient']:.2f}")
# print(f"Largest: {result['concentration']['largestHolderPercentage']:.1f}%")