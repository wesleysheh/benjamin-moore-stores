#!/usr/bin/env python3
"""Manual lookup of remaining stores using their BM store pages and business websites."""
import json, urllib.request, urllib.parse, re, time, sys

with open('mw_owner_progress.json') as f:
    data = json.load(f)

remaining = [(k,v) for k,v in data.items() if v.get('status') in ('needs_manual','not_found','searched')]

def fetch(url, max_chars=15000):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='ignore')[:max_chars]
    except Exception as e:
        return f"ERROR: {e}"

def clean_html(text):
    return re.sub(r'<[^>]+>', ' ', text).strip()

def search_buzzfile(name, city, state):
    """Search Buzzfile for business info."""
    q = urllib.parse.quote(f"{name} {city} {state}")
    url = f"https://www.buzzfile.com/Search/Company/Results?SearchTerm={q}"
    text = fetch(url, 10000)
    if 'ERROR' not in text:
        # Look for owner/contact info
        owner_match = re.search(r'(?:Contact|Owner|President|Manager).*?([A-Z][a-z]+\s[A-Z][a-z]+)', text)
        if owner_match:
            return owner_match.group(1)
    return None

def search_dandb(name, state):
    """Try D&B/Manta for business info."""
    state_full = {
        'AZ':'arizona','CO':'colorado','MT':'montana','NM':'new-mexico',
        'NV':'nevada','UT':'utah','ID':'idaho','WY':'wyoming','CA':'california'
    }.get(state, state.lower())
    slug = name.lower().replace(' ', '-').replace("'", '').replace('&', 'and').replace(',','').replace('.','')
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    url = f"https://www.manta.com/c/{slug}"
    text = fetch(url, 10000)
    if 'ERROR' not in text and '404' not in text[:200]:
        contact = re.search(r'(?:Contact|Owner|Principal).*?([A-Z][a-z]+\s[A-Z][a-z]+)', text)
        if contact:
            return contact.group(1)
    return None

# Try BM store detail pages for each store (they sometimes have owner info)
updated = 0
for store_num, store in remaining:
    name = store['name']
    city = store['city']
    state = store['state']
    url = f"https://www.benjaminmoore.com/en-us/store-locator/{store_num}"
    
    # Try the BM API for detailed store info
    api_url = f"https://api.benjaminmoore.io/retailer/stores/{store_num}?version=v1.0&locale=en-us"
    text = fetch(api_url)
    
    # Try to add the API key
    try:
        req = urllib.request.Request(api_url, headers={
            'Ocp-Apim-Subscription-Key': '48c3c3e75b424f97904f9659da65b4d0',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            detail = json.loads(r.read().decode('utf-8'))
        
        # Check if there's more info in the detail view
        if isinstance(detail, dict):
            website = detail.get('contact', {}).get('website', '') or detail.get('website', '')
            if website and not store.get('website'):
                store['website'] = website
                print(f"  {name}: got website: {website}", file=sys.stderr)
    except Exception as e:
        pass
    
    time.sleep(0.3)

# Now try to fetch each store's own website for About/Owner info
for store_num, store in remaining:
    name = store['name']
    email = store.get('email', '')
    website = store.get('website', '')
    
    # Extract domain from email if no website
    if not website and email:
        domain_match = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]+)', email)
        if domain_match:
            domain = domain_match.group(1)
            if domain not in ('gmail.com', 'yahoo.com', 'hotmail.com', 'icloud.com', 'aol.com'):
                website = f"https://{domain}"
    
    if website:
        if not website.startswith('http'):
            website = f"https://{website}"
        
        print(f"\n--- Checking website for {name}: {website} ---", file=sys.stderr)
        
        # Check about page
        for about_path in ['', '/about', '/about-us', '/about.html']:
            about_url = website.rstrip('/') + about_path
            text = fetch(about_url, 10000)
            if 'ERROR' not in text:
                cleaned = clean_html(text)
                # Look for owner patterns
                patterns = [
                    r'(?:owner|owned by|founded by|president|ceo|principal|proprietor)[:\s]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)',
                    r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)[\s,]+(?:is the |)(?:owner|president|ceo|founder)',
                    r'family[- ]owned.*?(?:by\s+)?(?:the\s+)?([A-Z][a-z]+)\s+family',
                ]
                for pat in patterns:
                    m = re.search(pat, cleaned, re.IGNORECASE)
                    if m:
                        store['owner_name'] = m.group(1).strip()
                        store['source'] = f'Website: {about_url}'
                        store['status'] = 'found'
                        updated += 1
                        print(f"  FOUND: {store['owner_name']}", file=sys.stderr)
                        break
                if store.get('status') == 'found':
                    break
            time.sleep(0.5)
    
    data[store_num] = store

with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nUpdated {updated} stores", file=sys.stderr)
from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
