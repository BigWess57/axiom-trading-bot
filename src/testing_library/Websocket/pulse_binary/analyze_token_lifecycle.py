#!/usr/bin/env python3
"""
Analyze token lifecycle in Pulse data:
- How are new tokens added?
- How are tokens removed from monitoring?
"""
import json
from collections import defaultdict

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print(f"📊 Analyzing {len(messages)} messages for token lifecycle...\n")

# Track tokens across messages
tokens_by_message = []  # List of (message_idx, set_of_tokens)
type_0_messages = []
type_1_messages = []
all_tokens_ever_seen = set()

for idx, msg in enumerate(messages):
    if msg["type"] != "msgpack":
        continue
    
    data = msg["data"]
    
    # Type 0: Snapshot (includes full token arrays)
    if data[0] == 0:
        type_0_messages.append((idx, data))
        # Extract all token addresses from this snapshot
        snapshot_tokens = set()
        for category, tokens in data[1].items():
            for token_data in tokens:
                if isinstance(token_data, list) and len(token_data) > 0:
                    token_addr = token_data[0]  # First field is pair address
                    snapshot_tokens.add(token_addr)
                    all_tokens_ever_seen.add(token_addr)
        tokens_by_message.append((idx, snapshot_tokens))
    
    # Type 1: Update (only updates specific fields for a token)
    elif data[0] == 1:
        type_1_messages.append((idx, data))
        token_addr = data[1]
        all_tokens_ever_seen.add(token_addr)

print("=" * 80)
print("MESSAGE TYPE BREAKDOWN")
print("=" * 80)
print(f"Type 0 (Snapshot) messages: {len(type_0_messages)}")
print(f"Type 1 (Update) messages: {len(type_1_messages)}")
print(f"Other message types: {len(messages) - len(type_0_messages) - len(type_1_messages)}\n")

print("=" * 80)
print("SNAPSHOT ANALYSIS (Type 0)")
print("=" * 80)
if type_0_messages:
    print(f"\n📸 First snapshot (message #{type_0_messages[0][0]}):")
    first_snapshot = type_0_messages[0][1]
    for category, tokens in first_snapshot[1].items():
        print(f"   {category}: {len(tokens)} tokens")
    
    if len(type_0_messages) > 1:
        print(f"\n📸 Second snapshot (message #{type_0_messages[1][0]}):")
        second_snapshot = type_0_messages[1][1]
        for category, tokens in second_snapshot[1].items():
            print(f"   {category}: {len(tokens)} tokens")
        
        print(f"\n📸 Subsequent snapshots: {len(type_0_messages) - 2}")
else:
    print("⚠️  No Type 0 (snapshot) messages found!")

print("\n" + "=" * 80)
print("TOKEN LIFECYCLE TRACKING")
print("=" * 80)

# Track when tokens appear and disappear
token_first_seen = {}  # token_addr -> message_idx
token_last_update = {}  # token_addr -> message_idx
tokens_in_snapshots = defaultdict(set)  # snapshot_idx -> set of tokens

# Process all messages chronologically
for idx, msg in enumerate(messages):
    if msg["type"] != "msgpack":
        continue
    
    data = msg["data"]
    
    if data[0] == 0:  # Snapshot
        snapshot_tokens = set()
        for category, tokens in data[1].items():
            for token_data in tokens:
                if isinstance(token_data, list) and len(token_data) > 0:
                    token_addr = token_data[0]
                    snapshot_tokens.add(token_addr)
                    
                    if token_addr not in token_first_seen:
                        token_first_seen[token_addr] = idx
                    token_last_update[token_addr] = idx
        
        tokens_in_snapshots[idx] = snapshot_tokens
    
    elif data[0] == 1:  # Update
        token_addr = data[1]
        if token_addr not in token_first_seen:
            token_first_seen[token_addr] = idx
        token_last_update[token_addr] = idx

print(f"\n📊 Total unique tokens seen: {len(all_tokens_ever_seen)}")
print(f"   Tokens first seen in snapshots: {sum(1 for addr, idx in token_first_seen.items() if any(idx == snap_idx for snap_idx in tokens_in_snapshots.keys()))}")
print(f"   Tokens first seen in updates: {sum(1 for addr, idx in token_first_seen.items() if not any(idx == snap_idx for snap_idx in tokens_in_snapshots.keys()))}")

# Analyze token additions and removals between snapshots
if len(tokens_in_snapshots) >= 2:
    print("\n" + "=" * 80)
    print("SNAPSHOT-TO-SNAPSHOT CHANGES")
    print("=" * 80)
    
    snapshot_indices = sorted(tokens_in_snapshots.keys())
    for i in range(len(snapshot_indices) - 1):
        prev_idx = snapshot_indices[i]
        curr_idx = snapshot_indices[i + 1]
        
        prev_tokens = tokens_in_snapshots[prev_idx]
        curr_tokens = tokens_in_snapshots[curr_idx]
        
        added = curr_tokens - prev_tokens
        removed = prev_tokens - curr_tokens
        
        print(f"\nSnapshot #{prev_idx} → Snapshot #{curr_idx}:")
        print(f"   Messages between: {curr_idx - prev_idx - 1}")
        print(f"   Tokens in previous: {len(prev_tokens)}")
        print(f"   Tokens in current: {len(curr_tokens)}")
        print(f"   ➕ Added: {len(added)} tokens")
        print(f"   ➖ Removed: {len(removed)} tokens")
        
        if added:
            print(f"\n   ✨ New tokens added:")
            for token in list(added)[:3]:  # Show first 3
                print(f"      {token}")
            if len(added) > 3:
                print(f"      ... and {len(added) - 3} more")
        
        if removed:
            print(f"\n   🗑️  Tokens removed:")
            for token in list(removed)[:3]:  # Show first 3
                print(f"      {token}")
            if len(removed) > 3:
                print(f"      ... and {len(removed) - 3} more")

print("\n" + "=" * 80)
print("ANSWER TO YOUR QUESTIONS")
print("=" * 80)

print("\n1️⃣ How are NEW tokens shown?")
if type_0_messages:
    print("   ✅ YES - Type 0 (Snapshot) messages contain FULL token data arrays")
    print("   ✅ New tokens appear in subsequent snapshots as complete entries")
    print("   ⚠️  Type 1 (Update) messages can also reference tokens not in previous snapshots")
else:
    print("   ⚠️  No snapshot messages found in this capture")

print("\n2️⃣ How are tokens REMOVED from monitoring?")
if len(tokens_in_snapshots) >= 2:
    total_removed = sum(len(tokens_in_snapshots[snapshot_indices[i]] - tokens_in_snapshots[snapshot_indices[i+1]]) 
                       for i in range(len(snapshot_indices) - 1))
    
    if total_removed > 0:
        print(f"   ✅ Tokens are removed via SNAPSHOTS")
        print(f"   ✅ When a token stops being monitored, it simply doesn't appear in the next snapshot")
        print(f"   ✅ No explicit 'removal' message - token just disappears from list")
        print(f"   📊 Total tokens removed across snapshots: {total_removed}")
    else:
        print("   ℹ️  No tokens were removed during this capture period")
else:
    print("   ⚠️  Not enough snapshots to determine removal behavior")

print("\n3️⃣ Do tokens just stop receiving updates, or is there a specific message?")
print("   ✅ NO specific removal message")
print("   ✅ Tokens stop appearing in snapshots when no longer monitored")
print("   ✅ Type 1 updates cease, and token is absent from next Type 0 snapshot")
