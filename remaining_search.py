#!/usr/bin/env python3
"""Search for remaining store owners using web fetches."""
import json, urllib.request, urllib.parse, re, time, sys

with open('mw_owner_progress.json') as f:
    data = json.load(f)

remaining = {k:v for k,v in data.items() if v.get('status') in ('needs_manual','not_found','searched')}

def fetch(url, max_chars=8000):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='ignore')[:max_chars]
    except Exception as e:
        return f"ERROR: {e}"

# For UT stores, try the OpenCorporates API
def search_opencorporates(name, state):
    q = urllib.parse.quote(name)
    jurisdiction = {'UT':'us_ut','NV':'us_nv','MT':'us_mt','AZ':'us_az','NM':'us_nm','CO':'us_co'}.get(state,'')
    url = f"https://api.opencorporates.com/v0.4/companies/search?q={q}&jurisdiction_code={jurisdiction}&per_page=5"
    text = fetch(url)
    try:
        d = json.loads(text)
        results = d.get('results',{}).get('companies',[])
        if results:
            c = results[0]['company']
            officers_url = c.get('opencorporates_url','').replace('https://opencorporates.com','https://api.opencorporates.com/v0.4') + '/officers'
            officers_text = fetch(officers_url)
            officers = []
            try:
                od = json.loads(officers_text)
                officers = [o['officer']['name'] for o in od.get('results',{}).get('officers',[])]
            except:
                pass
            return {
                'name': c.get('name',''),
                'status': c.get('current_status',''),
                'agent': c.get('agent_name',''),
                'address': c.get('registered_address_in_full',''),
                'officers': officers,
                'source': 'OpenCorporates'
            }
    except:
        pass
    return None

updated = 0
for store_num, store in sorted(remaining.items(), key=lambda x: x[1].get('state','')):
    name = store['name']
    city = store['city']
    state = store['state']
    print(f"\n--- Searching: {name} ({city}, {state}) ---", file=sys.stderr)
    
    # Try OpenCorporates
    result = search_opencorporates(name, state)
    if result and result.get('officers'):
        store['owner_name'] = ', '.join(result['officers'][:3])
        store['registered_agent'] = result.get('agent','')
        store['entity_name'] = result.get('name','')
        store['principal_address'] = result.get('address','')
        store['source'] = result['source']
        store['status'] = 'found'
        updated += 1
        print(f"  FOUND via OpenCorporates: {store['owner_name']}", file=sys.stderr)
    elif result and result.get('agent'):
        store['registered_agent'] = result.get('agent','')
        store['entity_name'] = result.get('name','')
        store['principal_address'] = result.get('address','')
        store['source'] = result['source']
        store['status'] = 'partial'
        updated += 1
        print(f"  PARTIAL via OpenCorporates: agent={store['registered_agent']}", file=sys.stderr)
    else:
        # Try a simpler name search
        simplified = re.sub(r'[^a-zA-Z\s]', '', name).strip()
        result2 = search_opencorporates(simplified, state)
        if result2 and (result2.get('officers') or result2.get('agent')):
            store['owner_name'] = ', '.join(result2.get('officers',[][:3]))
            store['registered_agent'] = result2.get('agent','')
            store['entity_name'] = result2.get('name','')
            store['principal_address'] = result2.get('address','')
            store['source'] = result2.get('source','OpenCorporates')
            store['status'] = 'found' if result2.get('officers') else 'partial'
            updated += 1
            print(f"  FOUND (simplified): {store.get('owner_name','')}", file=sys.stderr)
        else:
            print(f"  NOT FOUND", file=sys.stderr)
    
    data[store_num] = store
    time.sleep(0.5)  # rate limit

# Save updated progress
with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nUpdated {updated} stores", file=sys.stderr)

# Print summary
from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
print("Final status:", file=sys.stderr)
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
