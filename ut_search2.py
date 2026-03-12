#!/usr/bin/env python3
"""Search Utah SOS for remaining UT stores - using proper selectors."""
import json, time, sys, re
from playwright.sync_api import sync_playwright

UT_SEARCHES = [
    ("10002698", ["Wilson Paint", "Wilsons Paint"]),
    ("10004654", ["Salt Lake Paint"]),
    ("10006195", ["Bennett Paint"]),
    ("10008359", ["Layton True Value"]),
    ("10008429", ["Springville True Value"]),
    ("10009662", ["Sandy Paint"]),
    ("10009670", ["Rocky Mountain Paint"]),
    ("10011047", ["Plain City True Value"]),
    ("10011614", ["Farmington Paint"]),
    ("10013016", ["Fishlake Lumber"]),
]

with open('mw_owner_progress.json') as f:
    data = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    for store_num, search_terms in UT_SEARCHES:
        store = data[store_num]
        print(f"\n=== {store['name']} ({store['city']}) ===", file=sys.stderr)
        
        for search_term in search_terms:
            page.goto('https://businessregistration.utah.gov/EntitySearch/OnlineEntitySearch', timeout=20000)
            page.wait_for_timeout(2000)
            
            # Click Contains radio
            try:
                page.get_by_label('Contains').check()
            except:
                try:
                    page.locator('text=Contains').click()
                except:
                    pass
            
            page.wait_for_timeout(500)
            
            # Fill name field
            name_input = page.locator('input[type="text"]').first
            name_input.fill(search_term)
            
            # Click Search
            page.get_by_role('button', name='Search').click()
            page.wait_for_timeout(3000)
            
            content = page.content()
            
            # Dismiss alert if present
            try:
                page.get_by_role('button', name='OK').click(timeout=2000)
                print(f"  No results for '{search_term}'", file=sys.stderr)
                continue
            except:
                pass
            
            # We have results - look for Active ones
            page_text = page.locator('body').text_content()
            
            # Find all rows with Active status
            rows = page.locator('table tr').all()
            for row in rows:
                text = row.text_content() or ''
                if 'Active' in text and 'Current' in text:
                    entity_name = ''
                    cells = row.locator('td').all()
                    if cells:
                        entity_name = cells[0].text_content().strip()
                    print(f"  Active entity: {entity_name}", file=sys.stderr)
                    
                    # Click the link
                    try:
                        link = row.locator('a').first
                        link.click()
                        page.wait_for_timeout(3000)
                        
                        detail = page.locator('body').text_content()
                        lines = [l.strip() for l in detail.split('\n') if l.strip()]
                        
                        # Dump relevant lines
                        for i, line in enumerate(lines):
                            if any(kw in line for kw in ['Agent', 'Principal', 'Officer', 'Director', 'Member', 'Manager', 'Organizer', 'Address']):
                                context_lines = lines[max(0,i):min(len(lines),i+4)]
                                print(f"    {' | '.join(context_lines)}", file=sys.stderr)
                        
                        # Parse key info
                        for i, line in enumerate(lines):
                            if 'Registered Agent' in line:
                                for j in range(i+1, min(i+5, len(lines))):
                                    if lines[j] and lines[j] not in ('Name', 'Address', 'City', 'State', 'Zip'):
                                        store['registered_agent'] = lines[j]
                                        break
                            if any(kw in line for kw in ['Principal', 'Member', 'Manager', 'Organizer', 'Officer']):
                                for j in range(i+1, min(i+5, len(lines))):
                                    val = lines[j]
                                    if val and val not in ('Name', 'Address', 'City', 'State', 'Zip', 'Title') and len(val) > 2:
                                        if not store.get('owner_name') or store['owner_name'] in ('', 'Unknown', 'N/A'):
                                            store['owner_name'] = val
                                        break
                        
                        store['entity_name'] = entity_name
                        store['source'] = 'Utah SOS'
                        if store.get('owner_name') and store['owner_name'] not in ('', 'Unknown', 'N/A'):
                            store['status'] = 'found'
                        elif store.get('registered_agent'):
                            store['status'] = 'partial'
                        
                        data[store_num] = store
                        page.go_back()
                        page.wait_for_timeout(1000)
                        break
                    except Exception as e:
                        print(f"    Error: {e}", file=sys.stderr)
            
            if store.get('status') in ('found', 'partial'):
                break
    
    browser.close()

with open('mw_owner_progress.json', 'w') as f:
    json.dump(data, f, indent=2)

from collections import Counter
statuses = Counter(v.get('status') for v in data.values())
print("\nFinal:", file=sys.stderr)
for s,c in statuses.most_common():
    print(f"  {s}: {c}", file=sys.stderr)
