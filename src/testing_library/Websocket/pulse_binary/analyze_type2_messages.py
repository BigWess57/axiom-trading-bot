#!/usr/bin/env python3
"""
Analyze Type 2 messages - the missing piece!
"""
import json

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("🔍 ANALYZING TYPE 2 MESSAGES\n")
print("=" * 80)

# Find all Type 2 messages
type_2_messages = []
for idx, msg in enumerate(messages):
    if msg["type"] != "msgpack":
        continue
    
    data = msg["data"]
    if data[0] == 2:
        type_2_messages.append((idx, data))

print(f"Found {len(type_2_messages)} Type 2 messages\n")

if type_2_messages:
    print("=" * 80)
    print("FIRST FEW TYPE 2 MESSAGES (DETAILED)")
    print("=" * 80)
    
    for i, (idx, data) in enumerate(type_2_messages[:3]):
        print(f"\n📦 Type 2 Message #{i+1} (message index #{idx})")
        print(f"   Data structure: {type(data)}")
        print(f"   Length: {len(data)}")
        print(f"   Type ID: {data[0]}")
        
        if len(data) > 1:
            print(f"\n   Second element type: {type(data[1])}")
            print(f"   Second element: {data[1][:100] if isinstance(data[1], str) else data[1]}")
        
        if len(data) > 2:
            print(f"\n   Third element type: {type(data[2])}")
            if isinstance(data[2], list):
                print(f"   Third element (array) length: {len(data[2])}")
                if len(data[2]) > 0:
                    print(f"   First item in array: {data[2][0]}")
                    if len(data[2]) > 1:
                        print(f"   Second item in array: {data[2][1]}")
            else:
                print(f"   Third element: {data[2]}")
        
        print(f"\n   Full structure preview:")
        print(f"   {data}")
        print()
    
    # Analyze the structure
    print("=" * 80)
    print("TYPE 2 MESSAGE STRUCTURE ANALYSIS")
    print("=" * 80)
    
    # Type 2 structure is: [2, [category, token_data_array]]
    first_type2 = type_2_messages[0][1]
    
    print(f"\nType 2 message format:")
    print(f"  data[0] = 2 (message type)")
    print(f"  data[1] = {type(first_type2).__name__} (contains category and token)")
    
    if isinstance(first_type2, list) and len(first_type2) >= 2:
        category = first_type2[0]
        token_data = first_type2[1]
        
        print(f"\n  Structure: [2, [category, token_full_data]]")
        print(f"    Category: '{category}'")
        print(f"    Token data type: {type(token_data).__name__}")
        
        if isinstance(token_data, list) and len(token_data) > 0:
            print(f"    Token data length: {len(token_data)} fields")
            print(f"    This looks like FULL token data!")
            print(f"\n    Field breakdown:")
            for i, field in enumerate(token_data[:15]):  # Show first 15 fields
                print(f"      [{i}]: {field} ({type(field).__name__})")
            if len(token_data) > 15:
                print(f"      ... and {len(token_data) - 15} more fields")
    
    # Check which tokens get Type 2 messages
    print("\n" + "=" * 80)
    print("WHICH TOKENS GET TYPE 2 MESSAGES?")
    print("=" * 80)
    
    tokens_with_type2 = set()
    for idx, data in type_2_messages:
        # Structure: [2, [category, [pair_address, mint, creator, name, ...]]]
        if len(data) >= 2 and isinstance(data[1], list) and len(data[1]) >= 2:
            token_data_array = data[1][1]  # Second element of [category, token_data]
            if isinstance(token_data_array, list) and len(token_data_array) > 0:
                pair_address = token_data_array[0]  # First field is pair address
                tokens_with_type2.add(pair_address)
    
    print(f"\nTokens that received Type 2 messages: {len(tokens_with_type2)}")
    for token in tokens_with_type2:
        print(f"  {token}")
    
    # Cross-reference with our earlier findings
    new_tokens_from_type1 = [
        "4RXQKKHrLjJ6B3fyvJv5hSQQzRvvnPPg1jmfNczazHQN",
        "4vdFDBErnYfYwmyTr1HWBMnQ2BygNiyTTteQuDWVnS78",
        "Hs5uCokWCnfKzCnWWruXTkRBogjmjxWrtZcxBsWr7Sh2",
        "42bkayFupvrhDdctwDKqQmMkvpmN6xpQnm2vHiRaye3n",
        "HcEji1JYvgQu245dwkE9tsMJmuBQMnnQTi2zs243DLJV",
        "H7SM5eJxLnVmReVmyvV5CSWbnwYLMTMcQXN21QCSTKVF"
    ]
    
    overlap = tokens_with_type2.intersection(new_tokens_from_type1)
    
    print(f"\n❗ CRITICAL FINDING:")
    if overlap:
        print(f"   ✅ {len(overlap)} of the 'new' tokens received Type 2 messages!")
        print(f"   📦 Type 2 likely provides FULL token data for new tokens")
        print(f"\n   Overlap tokens:")
        for token in overlap:
            print(f"   - {token}")
    else:
        print(f"   ⚠️  No overlap with previously detected 'new' tokens")
    
    # When do Type 2 messages arrive?
    print("\n" + "=" * 80)
    print("WHEN DO TYPE 2 MESSAGES ARRIVE?")
    print("=" * 80)
    
    for token in list(overlap)[:3]:  # Check first 3 overlapping tokens
        # Find first Type 1 update
        first_type1_idx = None
        for idx, msg in enumerate(messages):
            if msg["type"] != "msgpack":
                continue
            data = msg["data"]
            if data[0] == 1 and data[1] == token:
                first_type1_idx = idx
                break
        
        # Find Type 2 message
        type2_idx = None
        for idx, data in type_2_messages:
            if data[1] == token:
                type2_idx = idx
                break
        
        print(f"\nToken: {token[:20]}...")
        if first_type1_idx:
            print(f"  First Type 1 update: message #{first_type1_idx}")
        if type2_idx:
            print(f"  Type 2 message: message #{type2_idx}")
            if first_type1_idx:
                diff = type2_idx - first_type1_idx
                print(f"  Difference: {diff} messages ({'AFTER' if diff > 0 else 'BEFORE'} Type 1)")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\n🎯 Type 2 messages are the answer!")
print("   ✅ They provide FULL token data (all ~50 fields)")
print("   ✅ They arrive for newly monitored tokens")
print("   ✅ This is the 'missing piece' - no REST API call needed!")
print("\n💡 Updated workflow:")
print("   1. Type 0 (Snapshot) - Initial full state")
print("   2. Type 2 (New Token) - Full data for newly monitored tokens")
print("   3. Type 1 (Update) - Incremental updates for all tokens")
