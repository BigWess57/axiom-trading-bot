#!/usr/bin/env python3
"""
Analyze the captured Pulse WebSocket data to understand the field mappings
"""
import json
from collections import Counter, defaultdict

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print(f"📊 Analyzing {len(messages)} messages...\n")

# Extract all MessagePack messages
msgpack_messages = [m for m in messages if m["type"] == "msgpack"]

print(f"MessagePack messages: {len(msgpack_messages)}")
print(f"Other types: {len(messages) - len(msgpack_messages)}\n")

# Analyze the structure
field_ids = Counter()
tokens_seen = set()
field_examples = defaultdict(list)

for msg in msgpack_messages:
    data = msg["data"]
    if len(data) == 3:
        msg_type, token_address, updates = data
        tokens_seen.add(token_address)
        
        for field_id, value in updates:
            field_ids[field_id] += 1
            # Store examples (limit to 3 per field)
            if len(field_examples[field_id]) < 3:
                field_examples[field_id].append({
                    "token": token_address[:20] + "...",
                    "value": value
                })

print(f"📈 Statistics:")
print(f"   Unique tokens: {len(tokens_seen)}")
print(f"   Unique fields: {len(field_ids)}\n")

print("🔍 Field ID Frequencies (sorted by occurrence):\n")
for field_id, count in sorted(field_ids.items(), key=lambda x: x[1], reverse=True):
    examples = field_examples[field_id]
    print(f"Field {field_id:3d}: {count:4d} updates")
    for ex in examples[:2]:  # Show first 2 examples
        print(f"         {ex['token']} → {ex['value']}")
    print()

print("\n💡 Field ID Guesses (based on common patterns):")
print("    13 - Likely price/liquidity metric (decimals)")
print("    16 - Likely price/value metric (decimals)")
print("    18-25 - Various market metrics")
print("    28-29 - Transaction counts (integers)")
print("    45 - Counter/metric (integers)")
print("\n✅ First few tokens seen:")
for i, token in enumerate(list(tokens_seen)[:5]):
    print(f"   {i+1}. {token}")
