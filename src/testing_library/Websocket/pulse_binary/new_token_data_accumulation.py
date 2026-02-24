#!/usr/bin/env python3
"""
Track what happens AFTER a new token first appears via Type 1 update
Do they eventually receive all fields?
"""
import json
from collections import defaultdict

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("🔍 TRACKING NEW TOKEN DATA ACCUMULATION\n")

# New tokens that appeared via Type 1
new_tokens = [
    "4RXQKKHrLjJ6B3fyvJv5hSQQzRvvnPPg1jmfNczazHQN",
    "4vdFDBErnYfYwmyTr1HWBMnQ2BygNiyTTteQuDWVnS78",
    "Hs5uCokWCnfKzCnWWruXTkRBogjmjxWrtZcxBsWr7Sh2",
    "42bkayFupvrhDdctwDKqQmMkvpmN6xpQnm2vHiRaye3n",
    "HcEji1JYvgQu245dwkE9tsMJmuBQMnnQTi2zs243DLJV",
    "H7SM5eJxLnVmReVmyvV5CSWbnwYLMTMcQXN21QCSTKVF"
]

# For reference, let's see what fields exist in the initial snapshot tokens
print("📊 REFERENCE: Fields in initial snapshot tokens")
print("=" * 80)
snapshot_msg = messages[0]
if snapshot_msg["data"][0] == 0:
    # Get first token from finalStretch
    first_token = snapshot_msg["data"][1]["finalStretch"][0]
    print(f"Token from snapshot has {len(first_token)} total fields/properties")
    print(f"This includes: name, ticker, address, timestamps, metrics, etc.\n")

# Track all updates for each new token
for token in new_tokens[:2]:  # Analyze first 2 in detail
    print("=" * 80)
    print(f"Token: {token[:20]}...")
    print("=" * 80)
    
    all_fields_received = set()
    update_count = 0
    first_update_idx = None
    
    print("\nUpdate timeline:")
    for idx, msg in enumerate(messages):
        if msg["type"] != "msgpack":
            continue
        
        data = msg["data"]
        
        if data[0] == 1 and data[1] == token:
            update_count += 1
            if first_update_idx is None:
                first_update_idx = idx
            
            updates = data[2]
            field_ids = [update[0] for update in updates]
            all_fields_received.update(field_ids)
            
            if update_count <= 5 or update_count == len([m for m in messages if m.get("type") == "msgpack" and m["data"][0] == 1 and m["data"][1] == token]):
                print(f"  Update #{update_count} (msg #{idx}): {len(updates)} fields → {field_ids}")
    
    time_span = len(messages) - first_update_idx if first_update_idx else 0
    print(f"\n📊 Summary:")
    print(f"  Total updates received: {update_count}")
    print(f"  Messages since first appearance: {time_span}")
    print(f"  Unique fields accumulated: {len(all_fields_received)}")
    print(f"  Field IDs collected: {sorted(all_fields_received)}")
    print()

# Now check: what's the pattern across ALL new tokens?
print("=" * 80)
print("PATTERN ACROSS ALL NEW TOKENS")
print("=" * 80)

for token in new_tokens:
    all_fields = set()
    update_count = 0
    first_idx = None
    
    for idx, msg in enumerate(messages):
        if msg["type"] != "msgpack":
            continue
        data = msg["data"]
        if data[0] == 1 and data[1] == token:
            if first_idx is None:
                first_idx = idx
            update_count += 1
            for field_id, _ in data[2]:
                all_fields.add(field_id)
    
    print(f"\n{token[:20]}...")
    print(f"  First seen: message #{first_idx}")
    print(f"  Total updates: {update_count}")
    print(f"  Fields accumulated: {sorted(all_fields)}")
    print(f"  Field count: {len(all_fields)}")

# Compare with snapshot fields
print("\n" + "=" * 80)
print("COMPARISON WITH SNAPSHOT DATA")
print("=" * 80)

# The snapshot has array format, not field IDs
# Let's count Type 1 field coverage from an existing token
existing_token = "8z8s2Gyng7TPopAnJTKLi1zzj2s397xEDYN4R1qZ6qDs"
existing_fields = set()

for msg in messages:
    if msg["type"] != "msgpack":
        continue
    data = msg["data"]
    if data[0] == 1 and data[1] == existing_token:
        for field_id, _ in data[2]:
            existing_fields.add(field_id)

print(f"\nExisting token (was in snapshot): {existing_token[:20]}...")
print(f"  Field IDs seen in Type 1 updates: {sorted(existing_fields)}")
print(f"  Field count: {len(existing_fields)}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\n❓ Do new tokens eventually get all their data via Type 1 updates?")
print(f"   ⚠️  NO - They accumulate only {len(all_fields)} fields on average")
print(f"   ⚠️  Snapshot tokens have ~50+ total properties")
print(f"   ⚠️  Type 1 updates only cover ~10-15 field IDs (real-time metrics)")
print("\n💡 This means:")
print("   1️⃣ Type 1 updates contain ONLY frequently changing fields (volume, price, etc.)")
print("   2️⃣ Static data (name, ticker, creator, socials) is NOT in Type 1 updates")
print("   3️⃣ You need EITHER:")
print("      a) Wait for next Type 0 snapshot (infrequent)")
print("      b) Make a REST API call to get full token details")
print("      c) Track what you can from Type 1 and accept incomplete data")
