#!/usr/bin/env python3
"""
Deep dive: Find tokens that appeared in Type 1 updates but not in initial snapshot
"""
import json

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("🔍 DETAILED TOKEN APPEARANCE ANALYSIS\n")

# Get tokens from initial snapshot
initial_snapshot = None
snapshot_tokens = set()

for idx, msg in enumerate(messages):
    if msg["type"] == "msgpack" and msg["data"][0] == 0:
        initial_snapshot = msg["data"]
        for category, tokens in initial_snapshot[1].items():
            for token_data in tokens:
                if isinstance(token_data, list) and len(token_data) > 0:
                    snapshot_tokens.add(token_data[0])
        print(f"📸 Initial snapshot (message #{idx}) contains {len(snapshot_tokens)} tokens:")
        for token in snapshot_tokens:
            print(f"   {token}")
        break

# Track first appearance of each token
first_appearances = {}
for idx, msg in enumerate(messages):
    if msg["type"] != "msgpack":
        continue
    
    data = msg["data"]
    
    if data[0] == 0:  # Snapshot
        for category, tokens in data[1].items():
            for token_data in tokens:
                if isinstance(token_data, list) and len(token_data) > 0:
                    token_addr = token_data[0]
                    if token_addr not in first_appearances:
                        first_appearances[token_addr] = (idx, "Type 0 Snapshot", category)
    
    elif data[0] == 1:  # Update
        token_addr = data[1]
        if token_addr not in first_appearances:
            first_appearances[token_addr] = (idx, "Type 1 Update", None)

print(f"\n📊 All {len(first_appearances)} tokens and their FIRST appearance:\n")

tokens_in_snapshot = []
tokens_via_update = []

for token, (msg_idx, msg_type, category) in sorted(first_appearances.items(), key=lambda x: x[1][0]):
    if msg_type == "Type 0 Snapshot":
        tokens_in_snapshot.append(token)
        print(f"✅ {token}")
        print(f"   First seen: Message #{msg_idx} (Snapshot - {category} category)")
    else:
        tokens_via_update.append(token)
        print(f"⚠️  {token}")
        print(f"   First seen: Message #{msg_idx} (Type 1 Update - NOT in initial snapshot!)")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Tokens in initial snapshot: {len(tokens_in_snapshot)}")
print(f"Tokens that appeared later via Type 1 updates: {len(tokens_via_update)}")

if tokens_via_update:
    print(f"\n❗ IMPORTANT FINDING:")
    print(f"   {len(tokens_via_update)} tokens started receiving Type 1 updates")
    print(f"   WITHOUT first appearing in a Type 0 snapshot!")
    print(f"\n   This means:")
    print(f"   1️⃣ Initial snapshot contains currently monitored tokens")
    print(f"   2️⃣ New tokens that START being monitored send Type 1 updates immediately")
    print(f"   3️⃣ There is NO 'new token snapshot' - they just start sending updates")
    
    print(f"\n   New tokens (not in initial snapshot):")
    for token in tokens_via_update:
        msg_idx = first_appearances[token][0]
        print(f"   - {token} (first update at message #{msg_idx})")

# Now let's check if there are any JSON "new_pairs" messages
print("\n" + "="*80)
print("CHECKING FOR JSON NEW_PAIRS MESSAGES")
print("="*80)

json_messages = [m for m in messages if m["type"] == "json"]
print(f"Found {len(json_messages)} JSON messages:")
for idx, msg in enumerate(messages):
    if msg["type"] == "json":
        print(f"\nJSON message at index #{idx}:")
        print(f"  {msg['data']}")
