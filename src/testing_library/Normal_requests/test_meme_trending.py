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
    # Get last transaction
    trending = client.get_trending_tokens()

    print("Number of tokens: ", len(trending))
    print()
    print("First token:")
    print("\n")
    print("Token pair address: ", trending[0][0])
    print("Token address: ", trending[0][1])
    print("Token name: ", trending[0][2])
    print("Token ticker: ", trending[0][3])
    print("Token image: ", trending[0][4])
    print("Token decimals: ", trending[0][5])
    print("Protocol: ", trending[0][6])
    print("Protocol details: ", trending[0][7])
    print("Previous market cap: ", trending[0][8])
    print("Market cap: ", trending[0][9])
    print("Market cap percent change: ", trending[0][10])
    print("Liquidity: ", trending[0][11])
    print("Volume: ", trending[0][12])
    print("Buy count: ", trending[0][13])
    print("Sell count: ", trending[0][14])
    print("Top 10 holders: ", trending[0][15])
    print("LP burned: ", trending[0][16])
    print("Mint authority: ", trending[0][17])
    print("Freeze authority: ", trending[0][18])
    print("DEX paid: ", trending[0][19])
    print("Website: ", trending[0][20])
    print("Twitter: ", trending[0][21])
    print("Telegram: ", trending[0][22])
    print("Discord: ", trending[0][23])
    print("Created at: ", trending[0][24])
    print("Extra: ", trending[0][25])
    print("Supply: ", trending[0][26])
    print("Twitter handle history: ", trending[0][27])
    print("Pair recent data: ", trending[0][28])
    print("User count: ", trending[0][29])
except Exception as e:
    raise Exception(f"❌ Error: {e}")