#!/usr/bin/env python3
"""Search for remaining store owners via state SOS websites."""
import json, urllib.request, urllib.parse, re, time, sys, html

with open('mw_owner_progress.json') as f:
    data = json.load(f)

remaining = {k:v for k,v in data.items() if v.get('status') in ('needs_manual','not_found','searched')}

def fetch(url, max_chars=20000):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode('utf-8', errors='ignore')[:max_chars]
    except Exception as e:
        return f"ERROR: {e}"

def search_mt_sos(name):
    """Montana SOS business search."""
    q = urllib.parse.quote(name)
    url = f"https://biz.sosmt.gov/search/business?businessName={q}&searchType=contains"
    text = fetch(url)
    # Parse results - look for business names and links
    matches = re.findall(r'href="/business/(\d+)"[^>]*>([^<]+)', text)
    if matches:
        bid, bname = matches[0]
        # Get detail page
        detail = fetch(f"https://biz.sosmt.gov/business/{bid}")
        agents = re.findall(r'Registered Agent.*?<[^>]*>([^<]+)', detail, re.DOTALL)
        principals = re.findall(r'(?:Principal|Officer|Director|Member|Manager).*?<[^>]*>([^<]+)', detail, re.DOTALL)
        return {
            'entity': bname.strip(),
            'agent': agents[0].strip() if agents else '',
            'officers': [p.strip() for p in principals[:5] if p.strip() and len(p.strip()) > 2],
        }
    return None

def search_nm_sos(name):
    """New Mexico SOS business search."""
    q = urllib.parse.quote(name)
    url = f"https://portal.sos.state.nm.us/BFS/online/CorporationBusinessSearch/CorporationBusinessInformation?businessName={q}"
    text = fetch(url)
    matches = re.findall(r'<td[^>]*>([^<]+)</td>', text)
    if matches:
        return {'raw': [m.strip() for m in matches[:20] if m.strip()]}
    return None

def search_ut_sos(name):
    """Utah business search via their API."""
    q = urllib.parse.quote(name)
    url = f"https://secure.utah.gov/bes/action/search?businessName={q}&type=Contains"
    text = fetch(url)
    # Try to extract business info
    matches = re.findall(r'<td[^>]*>([^<]+)</td>', text)
    if matches:
        return {'raw': [m.strip() for m in matches[:20] if m.strip()]}
    return None

def search_nv_sos(name):
    """Nevada SOS search."""
    q = urllib.parse.quote(name)
    url = f"https://esos.nv.gov/EntitySearch/BusinessInformation?businessName={q}"
    text = fetch(url)
    matches = re.findall(r'<td[^>]*>([^<]+)</td>', text)
    if matches:
        return {'raw': [m.strip() for m in matches[:20] if m.strip()]}
    return None

def search_az_sos(name):
    """Arizona Corporation Commission search."""
    q = urllib.parse.quote(name)
    url = f"https://ecorp.azcc.gov/BusinessSearch/BusinessInfo?businessName={q}"
    text = fetch(url)
    matches = re.findall(r'<td[^>]*>([^<]+)</td>', text)
    if matches:
        return {'raw': [m.strip() for m in matches[:20] if m.strip()]}
    return None

# Try Montana SOS for MT stores
updated = 0
for store_num, store in sorted(remaining.items(), key=lambda x: x[1].get('state','')):
    name = store['name']
    state = store['state']
    print(f"\n--- {name} ({store['city']}, {state}) ---", file=sys.stderr)
    
    result = None
    if state == 'MT':
        result = search_mt_sos(name)
    elif state == 'NM':
        result = search_nm_sos(name)
    elif state == 'UT':
        result = search_ut_sos(name)
    elif state == 'NV':
        result = search_nv_sos(name)
    elif state == 'AZ':
        result = search_az_sos(name)
    
    if result:
        print(f"  Result: {json.dumps(result)[:200]}", file=sys.stderr)
        if result.get('officers'):
            store['owner_name'] = ', '.join(result['officers'][:3])
            store['entity_name'] = result.get('entity','')
            store['registered_agent'] = result.get('agent','')
            store['source'] = f"{state} SOS"
            store['status'] = 'found'
            updated += 1
        elif result.get('agent'):
            store['registered_agent'] = result.get('agent','')
            store['entity_name'] = result.get('entity','')
            store['source'] = f"{state} SOS"
            store['status'] = 'partial'
            updated += 1
        elif result.get('raw'):
            store['source'] = f"{state} SOS - raw data"
            print(f"  Raw: {result['raw'][:5]}", file=sys.stderr)
    else:
        print(f"  No result from SOS", file=sys.stderr)
    
    data[store_num] = store
    time.sleep(1)

with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nUpdated {updated} stores", file=sys.stderr)
from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
