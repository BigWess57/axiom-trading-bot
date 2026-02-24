from axiomtradeapi import AxiomTradeClient
import os
from dotenv import load_dotenv

load_dotenv()

client = AxiomTradeClient(
    auth_token=os.getenv('AXIOM_AUTH_TOKEN'),
    refresh_token=os.getenv('AXIOM_REFRESH_TOKEN')
)

# Test the /meme/[address] RSC endpoint
test_address = "6UsqFUgUcjruxV3MTQ5stndeZvjcQBsQaRkxFdqD7HVh"
build_id = "BJki6plWoxyLpN9Yg2ovb"

url = f"https://axiom.trade/meme/{test_address}?chain=sol&_rsc={build_id}"

headers = {
    "RSC": "1",
    "Next-Url": f"/meme/{test_address}?chain=sol",
    "Accept": "*/*"
}

print(f"Testing: {url}")
response = client.auth_manager.make_authenticated_request('GET', url, headers=headers)

if response.status_code == 200:
    print(f"✅ Success! Length: {len(response.text)}")
    
    # Save
    with open("meme_detail_rsc.txt", "w") as f:
        f.write(response.text)
    print("Saved to meme_detail_rsc.txt")
    
    # Search for data
    keywords = ["marketCapSol", "bondingCurve", "migrated", "volumeSol"]
    for kw in keywords:
        if kw in response.text:
            print(f"✅ Found: {kw}")
            idx = response.text.find(kw)
            print(f"   Context: ...{response.text[max(0,idx-50):idx+100]}...")
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text[:500])
