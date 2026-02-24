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

import re
import json

def get_build_id(html):
    # Try multiple patterns
    patterns = [
        r'"buildId":"([a-zA-Z0-9_-]+)"',
        r'buildId:"([a-zA-Z0-9_-]+)"',
        r'static/([a-zA-Z0-9_-]+)/_buildManifest.js'
    ]
    for p in patterns:
        match = re.search(p, html)
        if match:
            return match.group(1)
    return None

# Fetch the main page HTML to extract the build ID
print("Fetching main page to find Build ID...")
# Use the public method instead of accessing internal session
response = client.auth_manager.make_authenticated_request('GET', "https://axiom.trade/pulse?chain=sol")

build_id = "BJki6plWoxyLpN9Yg2ovb" # discovered from previous response
if response.status_code == 200:
    found_id = get_build_id(response.text)
    if found_id:
        print(f"Found Build ID: {found_id}")
        build_id = found_id
    else:
        print("Could not find Build ID, using fallback.")

rsc_url = f"https://axiom.trade/pulse?chain=sol&_rsc={build_id}"

# Headers without Tree to force full load
headers = {
    "RSC": "1",
    "Next-Url": "/pulse",
    "Accept": "*/*",
    "Priority": "i"
}

# Make the RSC request using the authenticated session
print(f"Requesting: {rsc_url}")
try:
    rsc_response = client.auth_manager.make_authenticated_request('GET', rsc_url, headers=headers)

    if rsc_response.status_code == 200:
        print("✅ RSC Request Successful!")
        print(f"Response length: {len(rsc_response.text)} characters")
        
        # Save nested response
        with open("rsc_response.txt", "w", encoding="utf-8") as f:
            f.write(rsc_response.text)
        print("Saved raw response to rsc_response.txt")
        
        # Robust Search
        print("Searching for token data...")
        keywords = ["marketCapSol", "migrated", "bondingCurve", "FatCat", "Tiktok"]
        found = False
        
        for kw in keywords:
            if kw in rsc_response.text:
                print(f"✅ Found keyword: '{kw}'")
                found = True
                # Find the context
                idx = rsc_response.text.find(kw)
                start = max(0, idx - 100)
                end = min(len(rsc_response.text), idx + 200)
                print(f"Context: ...{rsc_response.text[start:end]}...")
        
        if not found:
            print("❌ No keywords found in response.")
            
    else:
        print(f"❌ RSC Request Failed: {rsc_response.status_code}")
        print(rsc_response.text[:500])

except Exception as e:
    print(f"❌ Error: {e}")
