#!/usr/bin/env python3
"""Scrape Benjamin Moore store locator for Mountain West + CA states, exclude Ace."""

import json, sys, time
from playwright.sync_api import sync_playwright

searches = [
    ('AZ', 'Phoenix, AZ'), ('AZ', 'Tucson, AZ'), ('AZ', 'Flagstaff, AZ'), ('AZ', 'Yuma, AZ'),
    ('CO', 'Denver, CO'), ('CO', 'Colorado Springs, CO'), ('CO', 'Grand Junction, CO'), ('CO', 'Durango, CO'),
    ('ID', 'Boise, ID'), ('ID', 'Idaho Falls, ID'), ('ID', 'Coeur d Alene, ID'),
    ('MT', 'Billings, MT'), ('MT', 'Missoula, MT'), ('MT', 'Great Falls, MT'),
    ('NV', 'Las Vegas, NV'), ('NV', 'Reno, NV'),
    ('NM', 'Albuquerque, NM'), ('NM', 'Santa Fe, NM'), ('NM', 'Las Cruces, NM'),
    ('UT', 'Salt Lake City, UT'), ('UT', 'St George, UT'), ('UT', 'Provo, UT'),
    ('WY', 'Cheyenne, WY'), ('WY', 'Casper, WY'), ('WY', 'Jackson, WY'),
    ('CA', 'Los Angeles, CA'), ('CA', 'San Francisco, CA'), ('CA', 'San Diego, CA'),
    ('CA', 'Sacramento, CA'), ('CA', 'Fresno, CA'), ('CA', 'Redding, CA'),
    ('CA', 'Bakersfield, CA'), ('CA', 'Santa Barbara, CA'), ('CA', 'Eureka, CA'),
]

captured_responses = []

def handle_response(response):
    url = response.url
    if ('store' in url.lower() or 'dealer' in url.lower()) and response.status == 200:
        try:
            text = response.text()
            if len(text) > 100 and '{' in text:
                captured_responses.append({'url': url, 'body': text})
        except:
            pass

all_stores = {}  # keyed by name+address for dedup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    
    for state, search_term in searches:
        page = context.new_page()
        captured_responses.clear()
        page.on('response', handle_response)
        
        try:
            page.goto('https://www.benjaminmoore.com/en-us/store-locator', timeout=20000)
        except:
            pass
        
        # Dismiss cookies
        try:
            page.click('button:has-text("Accept Cookies")', timeout=3000)
        except:
            pass
        
        try:
            inp = page.locator('input[placeholder*="Address"]')
            inp.fill(search_term)
            page.click('button:has-text("Search Address")')
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"[ERROR] {search_term}: {e}", file=sys.stderr)
            page.close()
            continue
        
        if captured_responses:
            for cr in captured_responses:
                print(f"[API] {search_term} -> {cr['url'][:200]}", file=sys.stderr)
                try:
                    data = json.loads(cr['body'])
                    # Try to find stores array in various possible structures
                    stores_list = None
                    if isinstance(data, list):
                        stores_list = data
                    elif isinstance(data, dict):
                        for key in ['stores', 'results', 'data', 'dealers', 'locations']:
                            if key in data:
                                stores_list = data[key]
                                break
                        if stores_list is None:
                            stores_list = [data]
                    
                    if stores_list:
                        for s in stores_list:
                            if isinstance(s, dict):
                                name = s.get('name', s.get('storeName', s.get('dealerName', '')))
                                addr = s.get('address', s.get('address1', s.get('street', '')))
                                city = s.get('city', '')
                                st = s.get('state', s.get('stateProvince', state))
                                phone = s.get('phone', s.get('phoneNumber', ''))
                                key = f"{name}|{addr}"
                                if key not in all_stores:
                                    all_stores[key] = {
                                        'name': name, 'address': addr, 'city': city,
                                        'state': st, 'phone': phone, 'raw': s
                                    }
                except json.JSONDecodeError:
                    pass
        else:
            # Read from DOM
            print(f"[DOM] {search_term}: reading store cards...", file=sys.stderr)
            try:
                # Try to find store listing elements
                cards = page.locator('li[class*="store"], div[class*="store"], div[class*="dealer"], a[class*="store"]').all()
                if not cards:
                    cards = page.locator('[data-testid*="store"]').all()
                
                for card in cards:
                    text = card.text_content().strip().replace('\n', ' | ')
                    key = text[:100]
                    if key not in all_stores:
                        all_stores[key] = {'raw_text': text, 'state': state, 'search': search_term}
                        
                if not cards:
                    # Last resort: grab all text from results area
                    content = page.content()
                    # Look for store data in Next.js __NEXT_DATA__
                    if '__NEXT_DATA__' in content:
                        import re
                        match = re.search(r'__NEXT_DATA__.*?=\s*({.*?})\s*</script>', content)
                        if match:
                            print(f"[NEXT] Found __NEXT_DATA__", file=sys.stderr)
                    
                    print(f"[DOM] {search_term}: no store cards found, trying snapshot", file=sys.stderr)
                    # Get visible text
                    visible = page.locator('main').text_content()
                    if visible and len(visible) > 50:
                        print(f"[VISIBLE] {search_term}: {visible[:500]}", file=sys.stderr)
                    
            except Exception as e:
                print(f"[DOM ERROR] {search_term}: {e}", file=sys.stderr)
        
        page.close()
    
    browser.close()

# Output results
print(f"\n=== Found {len(all_stores)} unique stores ===\n")
for key, store in sorted(all_stores.items()):
    print(json.dumps(store))
