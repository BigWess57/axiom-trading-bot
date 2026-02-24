#!/usr/bin/env python3
"""Analyze ALL message types in the Pulse data capture"""

import json
from collections import Counter, defaultdict

with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("=" * 80)
print("ALL MESSAGE TYPES ANALYSIS")
print("=" * 80)

# Count message types
type_counter = Counter()
type_examples = defaultdict(list)

for idx, msg_wrapper in enumerate(messages):
    # Extract the actual message data from the wrapper
    if isinstance(msg_wrapper, dict) and "data" in msg_wrapper:
        msg = msg_wrapper["data"]
    else:
        msg = msg_wrapper
    
    if isinstance(msg, list) and len(msg) > 0:
        msg_type = msg[0]
        type_counter[msg_type] += 1
        # Store first 3 examples of each type
        if len(type_examples[msg_type]) < 3:
            type_examples[msg_type].append((idx, msg))

print(f"\nMessage Type Distribution (Total: {len(messages)} messages):")
print("-" * 80)
for msg_type in sorted(type_counter.keys()):
    count = type_counter[msg_type]
    percentage = (count / len(messages)) * 100
    print(f"  Type {msg_type}: {count:4d} messages ({percentage:5.2f}%)")

print("\n" + "=" * 80)
print("DETAILED ANALYSIS BY TYPE")
print("=" * 80)

for msg_type in sorted(type_counter.keys()):
    print(f"\n{'=' * 80}")
    print(f"TYPE {msg_type} MESSAGES ({type_counter[msg_type]} total)")
    print(f"{'=' * 80}")
    
    if msg_type in [0, 1, 2]:
        print(f"  ✅ Already analyzed - see previous scripts")
        continue
    
    print(f"\n📦 Showing first 3 examples:\n")
    
    for example_idx, (msg_idx, msg_data) in enumerate(type_examples[msg_type]):
        print(f"Example #{example_idx + 1} (message index #{msg_idx})")
        print(f"  Length: {len(msg_data)}")
        print(f"  Structure: {type(msg_data).__name__}")
        
        # Show structure
        if len(msg_data) >= 2:
            print(f"  data[0] = {msg_data[0]} (type ID)")
            print(f"  data[1] = {type(msg_data[1]).__name__}")
            
            # If it's a list, show what's inside
            if isinstance(msg_data[1], list):
                print(f"    Length: {len(msg_data[1])}")
                if len(msg_data[1]) > 0:
                    print(f"    First element: {msg_data[1][0]}")
                    if isinstance(msg_data[1][0], str):
                        print(f"    → Looks like a token address")
            
            # Show full preview (limited)
            preview = str(msg_data)[:500]
            print(f"\n  Preview: {preview}...")
        
        print()

# Check if Type 3 exists and what tokens it affects
if 3 in type_counter:
    print("\n" + "=" * 80)
    print("🔍 TYPE 3 TOKEN ANALYSIS")
    print("=" * 80)
    
    type3_tokens = set()
    
    for msg in messages:
        if isinstance(msg, list) and len(msg) > 0 and msg[0] == 3:
            # Try to extract token identifier
            if len(msg) >= 2:
                if isinstance(msg[1], str):
                    type3_tokens.add(msg[1][:30] + "...")
                elif isinstance(msg[1], list) and len(msg[1]) > 0:
                    if isinstance(msg[1][0], str):
                        type3_tokens.add(msg[1][0][:30] + "...")
    
    print(f"\nTokens affected by Type 3 messages: {len(type3_tokens)}")
    for token in sorted(type3_tokens):
        print(f"  - {token}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total message types found: {len(type_counter)}")
print(f"Message types: {sorted(type_counter.keys())}")
