#!/usr/bin/env python3
"""Deep dive into Type 3 messages"""

import json

with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("=" * 80)
print("TYPE 3 MESSAGE DEEP DIVE")
print("=" * 80)

type3_messages = []

for idx, msg_wrapper in enumerate(messages):
    if isinstance(msg_wrapper, dict) and "data" in msg_wrapper:
        msg = msg_wrapper["data"]
    else:
        msg = msg_wrapper
    
    if isinstance(msg, list) and len(msg) > 0 and msg[0] == 3:
        type3_messages.append((idx, msg))

print(f"\nTotal Type 3 messages: {len(type3_messages)}\n")

# Analyze structure
print("=" * 80)
print("STRUCTURE ANALYSIS")
print("=" * 80)

for i, (msg_idx, msg) in enumerate(type3_messages):
    print(f"\n📦 Type 3 Message #{i+1} (message index #{msg_idx})")
    print(f"   Structure: {msg}")
    print(f"   Length: {len(msg)}")
    
    if len(msg) >= 2 and isinstance(msg[1], list) and len(msg[1]) >= 2:
        category = msg[1][0]
        token_addr = msg[1][1]
        print(f"   Category: '{category}'")
        print(f"   Token: {token_addr}")

# Check timing - when do Type 3 messages appear?
print("\n" + "=" * 80)
print("TIMING ANALYSIS")
print("=" * 80)

print("\nType 3 message timeline:")
for i, (msg_idx, msg) in enumerate(type3_messages):
    category = msg[1][0] if len(msg) >= 2 and isinstance(msg[1], list) else "unknown"
    token = msg[1][1][:30] if len(msg) >= 2 and isinstance(msg[1], list) and len(msg[1]) >= 2 else "unknown"
    print(f"  Message #{msg_idx:4d}: [{category}] {token}...")

# Check if these tokens received Type 2 (add) messages
print("\n" + "=" * 80)
print("CORRELATION WITH TYPE 2 (NEW TOKEN) MESSAGES")
print("=" * 80)

# Extract Type 2 tokens
type2_tokens = set()
for msg_wrapper in messages:
    if isinstance(msg_wrapper, dict) and "data" in msg_wrapper:
        msg = msg_wrapper["data"]
    else:
        msg = msg_wrapper
    
    if isinstance(msg, list) and len(msg) > 0 and msg[0] == 2:
        if len(msg) >= 2 and isinstance(msg[1], list) and len(msg[1]) >= 2:
            token_data = msg[1][1]
            if isinstance(token_data, list) and len(token_data) > 0:
                type2_tokens.add(token_data[0])  # pair address

# Extract Type 3 tokens  
type3_tokens = []
for msg_idx, msg in type3_messages:
    if len(msg) >= 2 and isinstance(msg[1], list) and len(msg[1]) >= 2:
        type3_tokens.append((msg_idx, msg[1][0], msg[1][1]))

print(f"\nType 2 (New Token) messages: {len(type2_tokens)} unique tokens")
print(f"Type 3 messages: {len(type3_tokens)} tokens\n")

for msg_idx, category, token in type3_tokens:
    was_type2 = "✅ YES" if token in type2_tokens else "❌ NO"
    print(f"  Message #{msg_idx}: {token[:30]}... → Was in Type 2? {was_type2}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\n🎯 Type 3 Structure: [3, [category, token_address]]")
print("📊 Appears to be a REMOVAL message!")
print("   - Same format as Type 2 but with type ID 3")
print("   - Specifies category and token to remove")
