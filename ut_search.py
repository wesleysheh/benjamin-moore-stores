#!/usr/bin/env python3
"""Search Utah SOS for remaining UT stores using Playwright."""
import json, time, sys, re
from playwright.sync_api import sync_playwright

UT_STORES = [
    ("10002698", "Wilson's Paint", "KAYSVILLE"),
    ("10004654", "Salt Lake Paint", "SALT LAKE CITY"),
    ("10006195", "Bennett Paint", "LOGAN"),
    ("10008359", "Layton True Value", "LAYTON"),
    ("10008429", "Springville True Value", "SPRINGVILLE"),
    ("10009662", "Sandy Paint", "SANDY"),
    ("10009670", "Rocky Mountain Paint", "SOUTH JORDAN"),
    ("10011047", "Plain City True Value", "PLAIN CITY"),
    ("10011614", "Farmington Paint", "FARMINGTON"),
    ("10013016", "Fishlake Lumber", "BEAVER"),
    ("10017894", "Rocky Mountain Paint", "COTTONWOOD HEIGHTS"),
    ("10019286", "Rocky Mountain Paint", "SARATOGA SPRINGS"),
]

with open('mw_owner_progress.json') as f:
    data = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # non-headless for reliability
    page = browser.new_page()
    
    for store_num, search_name, city in UT_STORES:
        print(f"\n=== {search_name} ({city}) ===", file=sys.stderr)
        
        page.goto('https://businessregistration.utah.gov/EntitySearch/OnlineEntitySearch', timeout=15000)
        page.wait_for_timeout(1000)
        
        # Select "Contains"
        page.click('input[value="Contains"]')
        
        # Type search name
        page.fill('input[placeholder="Name:"]', search_name)
        page.click('button:has-text("Search")')
        page.wait_for_timeout(3000)
        
        # Check for results
        content = page.content()
        
        # Check for "No records found"
        if 'No records found' in content:
            print(f"  No records found for '{search_name}'", file=sys.stderr)
            # Try shorter name
            short_name = search_name.split()[0] + ' ' + search_name.split()[-1] if len(search_name.split()) > 1 else search_name
            if short_name != search_name:
                page.goto('https://businessregistration.utah.gov/EntitySearch/OnlineEntitySearch', timeout=15000)
                page.wait_for_timeout(1000)
                try:
                    page.click('button:has-text("OK")', timeout=2000)
                except:
                    pass
                page.click('input[value="Contains"]')
                page.fill('input[placeholder="Name:"]', short_name)
                page.click('button:has-text("Search")')
                page.wait_for_timeout(3000)
                content = page.content()
                if 'No records found' in content:
                    print(f"  No records found for '{short_name}' either", file=sys.stderr)
                    continue
        
        # Look for matching Active entities
        rows = page.locator('tr').all()
        found_entity = None
        for row in rows:
            text = row.text_content()
            if text and 'Active' in text and ('Current' in text or 'Good Standing' in text):
                # Check if name is relevant
                cells = row.locator('td').all()
                if cells:
                    entity_name = cells[0].text_content().strip()
                    # Click to get details
                    try:
                        link = row.locator('a').first
                        link.click()
                        page.wait_for_timeout(2000)
                        
                        detail_content = page.content()
                        # Extract principal/agent info
                        print(f"  Found entity: {entity_name}", file=sys.stderr)
                        
                        # Look for principal names, registered agent
                        agent_match = re.search(r'Registered Agent.*?([A-Z][A-Z\s,.-]+)', detail_content)
                        principal_matches = re.findall(r'(?:Principal|Officer|Director|Member|Manager|Organizer).*?Name.*?>([^<]+)<', detail_content)
                        
                        # Get page text for better parsing
                        detail_text = page.locator('body').text_content()
                        
                        # Store the detail text for manual review
                        store = data.get(store_num, {})
                        store['entity_name'] = entity_name
                        store['source'] = 'Utah SOS'
                        
                        # Try to find agent/principal in the detail text
                        lines = [l.strip() for l in detail_text.split('\n') if l.strip()]
                        for i, line in enumerate(lines):
                            if 'Registered Agent' in line and i+1 < len(lines):
                                store['registered_agent'] = lines[i+1]
                            if 'Principal' in line and i+1 < len(lines):
                                if not store.get('owner_name') or store['owner_name'] in ('', 'Unknown', 'N/A'):
                                    store['owner_name'] = lines[i+1]
                        
                        if store.get('owner_name') and store['owner_name'] not in ('', 'Unknown', 'N/A'):
                            store['status'] = 'found'
                            print(f"  Owner: {store['owner_name']}", file=sys.stderr)
                        elif store.get('registered_agent'):
                            store['status'] = 'partial'
                            print(f"  Agent: {store['registered_agent']}", file=sys.stderr)
                        
                        data[store_num] = store
                        found_entity = entity_name
                        
                        # Go back
                        page.go_back()
                        page.wait_for_timeout(1000)
                        break
                    except Exception as e:
                        print(f"  Error clicking: {e}", file=sys.stderr)
        
        if not found_entity:
            print(f"  No active entity found", file=sys.stderr)
    
    browser.close()

with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
print("\nFinal:", file=sys.stderr)
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
