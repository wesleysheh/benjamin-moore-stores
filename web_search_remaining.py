#!/usr/bin/env python3
"""Search for store owners using DuckDuckGo lite (HTML-based, no JS needed)."""
import json, urllib.request, urllib.parse, re, time, sys

with open('mw_owner_progress.json') as f:
    data = json.load(f)

remaining = [(k,v) for k,v in data.items() if v.get('status') in ('needs_manual','not_found','searched')]

def ddg_search(query):
    """Search DuckDuckGo HTML version."""
    q = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={q}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode('utf-8', errors='ignore')
        # Extract snippets
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
        snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:5]]
        return snippets
    except Exception as e:
        return [f"ERROR: {e}"]

updated = 0
results_log = []

for store_num, store in remaining:
    name = store['name']
    city = store['city']
    state = store['state']
    
    # Search for owner info
    query = f'"{name}" {city} {state} owner'
    print(f"\n--- {name} ({city}, {state}) ---", file=sys.stderr)
    
    snippets = ddg_search(query)
    owner_found = False
    
    for snippet in snippets:
        # Look for owner-related patterns
        owner_patterns = [
            r'(?:owner|owned by|founded by|president|ceo|principal|proprietor)[:\s]+([A-Z][a-z]+\s[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s[A-Z][a-z]+)[\s,]+(?:owner|president|ceo|founder|principal)',
        ]
        for pat in owner_patterns:
            m = re.search(pat, snippet, re.IGNORECASE)
            if m:
                store['owner_name'] = m.group(1).strip()
                store['source'] = 'Web search (DuckDuckGo)'
                store['status'] = 'found'
                owner_found = True
                updated += 1
                print(f"  FOUND: {store['owner_name']}", file=sys.stderr)
                break
        if owner_found:
            break
    
    if not owner_found and snippets:
        # Try broader search
        query2 = f'"{name}" {city} {state} LLC Inc Corp registered'
        snippets2 = ddg_search(query2)
        all_snippets = snippets + snippets2
        results_log.append({
            'store': name, 'city': city, 'state': state,
            'snippets': all_snippets[:6]
        })
        print(f"  Not found. Snippets: {snippets[:2]}", file=sys.stderr)
    
    data[store_num] = store
    time.sleep(2)  # rate limit DDG

with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

with open('remaining_search_log.json', 'w') as f:
    json.dump(results_log, f, indent=2)

print(f"\nUpdated {updated} stores", file=sys.stderr)
from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
