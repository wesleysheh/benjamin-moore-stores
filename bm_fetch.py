#!/usr/bin/env python3
"""Fetch all BM stores, filter Mountain West + CA, exclude Ace."""
import json, urllib.request, sys

API = "https://api.benjaminmoore.io/retailer/stores"
KEY = "48c3c3e75b424f97904f9659da65b4d0"
TARGET_STATES = {'AZ','CO','ID','MT','NV','NM','UT','WY','CA'}

all_stores = []
offset = 0
limit = 500

while True:
    url = f"{API}?version=v1.0&latitude=39.7&longitude=-104.9&radius=100&limit={limit}&offset={offset}&locale=en-us&countryCode=US"
    req = urllib.request.Request(url, headers={
        'Ocp-Apim-Subscription-Key': KEY,
        'Accept': 'application/json'
    })
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    
    stores = data.get('stores', [])
    total = data.get('total', 0)
    is_last = data.get('is_last', True)
    
    print(f"offset={offset}, got={len(stores)}, total={total}, is_last={is_last}", file=sys.stderr)
    all_stores.extend(stores)
    
    if is_last or not stores:
        break
    offset += limit

print(f"Total stores fetched: {len(all_stores)}", file=sys.stderr)

# Filter by target states and exclude Ace
filtered = []
for s in all_stores:
    state = s.get('location', {}).get('statecode', '')
    name = s.get('description', {}).get('name', '')
    
    if state not in TARGET_STATES:
        continue
    if 'ACE' in name.upper():
        continue
    
    filtered.append({
        'name': name,
        'number': s['description'].get('number', ''),
        'address': s['location'].get('address', ''),
        'city': s['location'].get('city', ''),
        'state': state,
        'zip': s['location'].get('zipcode', ''),
        'phone': s.get('contact', {}).get('phone', ''),
        'website': s.get('contact', {}).get('website', ''),
        'signature': s['description'].get('signature_store', False),
        'url': s['description'].get('url', ''),
    })

print(f"Filtered (Mountain West + CA, no Ace): {len(filtered)}", file=sys.stderr)

# Sort by state then city
filtered.sort(key=lambda x: (x['state'], x['city'], x['name']))

# Save
with open('/Users/clawbox-1/.openclaw/workspace/bm_stores_filtered.json', 'w') as f:
    json.dump(filtered, f, indent=2)

# Also make a CSV
with open('/Users/clawbox-1/.openclaw/workspace/bm_stores_filtered.csv', 'w') as f:
    f.write('State,City,Name,Address,Zip,Phone,Website,BM URL\n')
    for s in filtered:
        row = [s['state'], s['city'], s['name'], s['address'], s['zip'], s['phone'], s['website'], s['url']]
        f.write(','.join('"' + str(v).replace('"','""') + '"' for v in row) + '\n')

# Print summary by state
from collections import Counter
state_counts = Counter(s['state'] for s in filtered)
print("\n=== Stores by State (excl. Ace) ===", file=sys.stderr)
for st in sorted(state_counts):
    print(f"  {st}: {state_counts[st]}", file=sys.stderr)
print(f"  TOTAL: {len(filtered)}", file=sys.stderr)
