#!/usr/bin/env python3
"""
Examine the FIRST Type 1 message for new tokens to see if there's a pattern
"""
import json

# Load the captured data
with open("parsed_data/pulse_messages.json", "r") as f:
    messages = json.load(f)

print("🔍 EXAMINING FIRST TYPE 1 UPDATE FOR NEW TOKENS\n")

# Tokens that first appeared via Type 1 updates (from previous analysis)
new_tokens = [
    "4RXQKKHrLjJ6B3fyvJv5hSQQzRvvnPPg1jmfNczazHQN",
    "4vdFDBErnYfYwmyTr1HWBMnQ2BygNiyTTteQuDWVnS78",
    "Hs5uCokWCnfKzCnWWruXTkRBogjmjxWrtZcxBsWr7Sh2",
    "42bkayFupvrhDdctwDKqQmMkvpmN6xpQnm2vHiRaye3n",
    "HcEji1JYvgQu245dwkE9tsMJmuBQMnnQTi2zs243DLJV",
    "H7SM5eJxLnVmReVmyvV5CSWbnwYLMTMcQXN21QCSTKVF"
]

# Find the FIRST message for each new token
for token in new_tokens:
    for idx, msg in enumerate(messages):
        if msg["type"] != "msgpack":
            continue
        
        data = msg["data"]
        
        if data[0] == 1 and data[1] == token:
            updates = data[2]
            field_ids = [update[0] for update in updates]
            
            print(f"Token: {token}")
            print(f"  First update: Message #{idx}")
            print(f"  Number of fields: {len(updates)}")
            print(f"  Field IDs: {field_ids}")
            print(f"  Field details:")
            for field_id, value in updates[:10]:  # Show first 10 fields
                print(f"    Field {field_id}: {value}")
            if len(updates) > 10:
                print(f"    ... and {len(updates) - 10} more fields")
            print()
            break

print("\n" + "="*80)
print("PATTERN ANALYSIS")
print("="*80)

# Check if first messages have many fields (indicating full data)
first_update_field_counts = []
for token in new_tokens:
    for idx, msg in enumerate(messages):
        if msg["type"] != "msgpack":
            continue
        
        data = msg["data"]
        
        if data[0] == 1 and data[1] == token:
            first_update_field_counts.append(len(data[2]))
            break

print(f"Field counts in FIRST Type 1 update for new tokens:")
print(f"  {first_update_field_counts}")
print(f"  Average: {sum(first_update_field_counts) / len(first_update_field_counts):.1f} fields")
print()
print("For comparison, let's check regular Type 1 updates:")

# Sample some regular Type 1 updates from existing tokens
regular_update_counts = []
existing_token = "8z8s2Gyng7TPopAnJTKLi1zzj2s397xEDYN4R1qZ6qDs"  # From initial snapshot

for idx, msg in enumerate(messages[1:50]):  # Sample first 50 messages
    if msg["type"] != "msgpack":
        continue
    
    data = msg["data"]
    
    if data[0] == 1 and data[1] == existing_token:
        regular_update_counts.append(len(data[2]))

print(f"Field counts in regular Type 1 updates for existing tokens:")
print(f"  {regular_update_counts}")
if regular_update_counts:
    print(f"  Average: {sum(regular_update_counts) / len(regular_update_counts):.1f} fields")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
if first_update_field_counts and regular_update_counts:
    avg_first = sum(first_update_field_counts) / len(first_update_field_counts)
    avg_regular = sum(regular_update_counts) / len(regular_update_counts)
    
    if avg_first > avg_regular * 2:
        print("✅ NEW tokens get a Type 1 update with MANY fields (likely full initial data)")
        print("✅ EXISTING tokens get Type 1 updates with FEW fields (just changes)")
        print("\n💡 This means:")
        print("   - When a token starts being monitored, it sends a Type 1 with ~all fields")
        print("   - This is effectively a 'partial snapshot' for just that token")
        print("   - Subsequent updates only include changed fields")
    else:
        print("⚠️  No clear pattern difference between first and regular updates")
