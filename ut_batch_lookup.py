#!/usr/bin/env python3
"""Batch UT business entity lookup using Playwright on the new UT SOS site."""
import json
import re
import time
from playwright.sync_api import sync_playwright

UT_STORES = [
    ("10002698", "wilson's paint"),
    ("10004654", "salt lake paint"),
    ("10006195", "bennett paint"),
    ("10008359", "layton true value"),
    ("10008429", "springville true value"),
    ("10009662", "sandy paint"),
    ("10009670", "rocky mountain paint"),
    ("10011047", "plain city true value"),
    ("10011614", "farmington paint"),
    ("10013016", "fishlake lumber"),
    ("10017894", "rocky mountain paint"),
    ("10019286", "rocky mountain paint"),
]

BASE = "https://businessregistration.utah.gov"

def search_and_get_detail(page, search_term):
    """Search UT SOS and get first active matching entity details."""
    page.goto(f"{BASE}/EntitySearch/OnlineEntitySearch", wait_until="networkidle", timeout=20000)
    time.sleep(1)
    
    # Fill search
    name_input = page.query_selector('input[placeholder="Name:"]')
    if not name_input:
        inputs = page.query_selector_all('input[type="text"]')
        name_input = inputs[0] if inputs else None
    
    if not name_input:
        # Try by label
        name_input = page.locator('text=Name:').locator('..').locator('input').first
    
    if not name_input:
        return {"error": "No name input found"}
    
    name_input.fill(search_term)
    
    # Click search
    page.click('button:has-text("Search")')
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(1)
    
    # Find active entities in results
    rows = page.query_selector_all('table tbody tr')
    active_link = None
    for row in rows:
        text = row.inner_text()
        if 'Active' in text and 'Current' in text:
            link = row.query_selector('a')
            if link:
                active_link = link
                break
    
    if not active_link:
        # Take first non-empty link
        for row in rows:
            link = row.query_selector('a')
            if link and link.inner_text().strip():
                active_link = link
                break
    
    if not active_link:
        return {"error": f"No matching entity found for {search_term}"}
    
    entity_name = active_link.inner_text().strip()
    active_link.click()
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(1)
    
    # Extract detail page info
    text = page.inner_text('body')
    
    result = {"entity_name": entity_name}
    
    # Extract agent
    agent_m = re.search(r'Name:\s*(.+?)\s*Registered Agent Type:', text)
    if agent_m:
        result['agent'] = agent_m.group(1).strip()
    
    # Extract address
    addr_m = re.search(r'Street Address:\s*(.+?)\s*Last Updated:', text)
    if addr_m:
        result['address'] = addr_m.group(1).strip()
    
    # Extract principals from table
    principals = re.findall(r'(Director|President|Secretary|Manager|Member|Applicant|Officer)\s+(\S.*?)\s+(\d{1,2}[^,]+(?:,\s*\w+){2,})', text)
    if principals:
        result['principals'] = [{"title": p[0], "name": p[1].strip(), "address": p[2].strip()} for p in principals]
    
    # Entity number
    num_m = re.search(r'Entity Number:\s*(\S+)', text)
    if num_m:
        result['entity_number'] = num_m.group(1)
    
    # Physical address
    phys_m = re.search(r'Physical Address:\s*(.+?)\s*Updated Date:', text)
    if phys_m:
        result['physical_address'] = phys_m.group(1).strip()
    
    # Status
    status_m = re.search(r'Entity Status:\s*(\w+)', text)
    if status_m:
        result['status'] = status_m.group(1)
    
    result['raw'] = text[:3000]
    
    return result


def main():
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless to avoid blocks
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        for sid, search_term in UT_STORES:
            try:
                result = search_and_get_detail(page, search_term)
                results[sid] = result
                if 'error' not in result:
                    print(f"✓ {sid} {search_term}: {result.get('entity_name','')} -> Agent: {result.get('agent','')}")
                else:
                    print(f"✗ {sid} {search_term}: {result['error'][:100]}")
            except Exception as e:
                print(f"✗ {sid} {search_term}: {e}")
                results[sid] = {"error": str(e)}
            time.sleep(2)
        
        browser.close()
    
    with open('ut_sos_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Update progress file
    with open('mw_owner_progress.json') as f:
        data = json.load(f)
    
    count = 0
    for sid, search_term in UT_STORES:
        if sid in results and 'error' not in results[sid]:
            r = results[sid]
            agent = r.get('agent', '')
            principals_str = ''
            if 'principals' in r:
                principals_str = ', '.join(f"{p['name']} ({p['title']})" for p in r['principals'])
            
            data[sid].update({
                'owner_name': principals_str or agent,
                'registered_agent': agent,
                'principal_address': r.get('physical_address', r.get('address', '')),
                'business_entity': f"{r.get('entity_name', '')} (UT, Entity {r.get('entity_number', '')})",
                'source': 'Utah Division of Corporations',
                'status': 'found'
            })
            count += 1
            print(f"  Updated {sid}: {data[sid]['name']}")
    
    with open('mw_owner_progress.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nUpdated {count} UT stores")

if __name__ == '__main__':
    main()
