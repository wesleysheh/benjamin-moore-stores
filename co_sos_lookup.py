#!/usr/bin/env python3
"""Batch CO SOS entity lookup using Playwright."""
import json
import sys
import time
from playwright.sync_api import sync_playwright

SEARCHES = [
    # (store_ids, search_term, expected_name_fragment)
    (["10004865"], "manweiler hardware", "MANWEILER HARDWARE"),
    (["10001224"], "wylie paint", "WYLIE"),
    (["10002722"], "park supply rental", "PARK SUPPLY"),
    (["10002922"], "home store lamar", "HOME STORE"),  
    (["10003533"], "wray lumber", "WRAY LUMBER"),
    (["10003839"], "poncha lumber", "PONCHA LUMBER"),
    (["10004023"], "mountain high paint", "MOUNTAIN HIGH PAINT"),
    (["10006322"], "collbran supply", "COLLBRAN SUPPLY"),
    (["10006789"], "mountain color", "MOUNTAIN COLOR"),
    (["10006839"], "northside paint", "NORTHSIDE PAINT"),
    (["10006980"], "arkansas valley lumber", "ARKANSAS VALLEY"),
    (["10009824"], "noco paint", "NOCO PAINT"),
    (["10010512"], "g4 coatings", "G4 COATINGS"),
    (["10011128"], "juniper paints", "JUNIPER"),
    (["10012449"], "ajax supply", "AJAX SUPPLY"),
    (["10012697"], "arvada flooring", "ARVADA FLOORING"),
    (["10013065"], "herman lumber", "HERMAN LUMBER"),
    (["10013129"], "la junta trading", "LA JUNTA"),
    (["10013163"], "pandhandle creek", "PANDHANDLE"),
    (["10013336"], "stratton equity", "STRATTON EQUITY"),
    (["10013825"], "pronghorn country", "PRONGHORN"),
    (["10014576"], "choice building supply", "CHOICE BUILDING"),
    (["10014582"], "delta hardware inc", "DELTA HARDWARE"),
    (["10014639"], "valley hardware", "VALLEY HARDWARE"),
    (["10015646"], "steve paint supply", "STEVE"),
    (["10016432"], "agfinity", "AGFINITY"),
    (["10016433"], "poudre valley", "POUDRE VALLEY"),
    (["10017578"], "aguilar mercantile", "AGUILAR"),
    (["10018256"], "m m decorating", "DECORATING"),
    (["10019644"], "colored red", "COLORED RED"),
    (["10021008"], "budget home supply", "BUDGET HOME"),
    (["10021558"], "paint pallet", "PAINT PALLET"),
    (["10021993"], "lamar bms", "LAMAR BMS"),
    (["10000481"], "colors inc durango", "COLORS"),
]

def search_co_sos(page, search_term, expected_fragment):
    """Search CO SOS and return entity detail for best match."""
    # Go to search page
    page.goto("https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do?resetTransTyp=Y", wait_until="domcontentloaded")
    time.sleep(0.5)
    
    # Fill and submit
    text_input = page.query_selector('input[type="text"]')
    if not text_input:
        return None
    text_input.fill(search_term)
    form = page.query_selector('form')
    if form:
        form.evaluate('f => f.submit()')
    time.sleep(1)
    
    # Get results text
    text = page.inner_text('body')
    
    # Find Good Standing entities
    lines = text.split('\n')
    best_id = None
    best_file = None
    for line in lines:
        if 'Good Standing' in line and expected_fragment.upper() in line.upper():
            # Extract ID from the line
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                best_id = parts[1].strip()
                best_file = parts[2].strip() if len(parts) > 2 else best_id
                break
    
    # If no Good Standing, try Name Changed or Effective
    if not best_id:
        for line in lines:
            if expected_fragment.upper() in line.upper() and ('Name Changed' in line or 'Effective' in line):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    best_id = parts[1].strip()
                    best_file = parts[2].strip() if len(parts) > 2 else best_id
                    break
    
    if not best_id:
        return {"error": f"No matching entity for {search_term}", "raw": text[:500]}
    
    # Navigate to entity detail
    url = f"https://www.sos.state.co.us/biz/BusinessEntityDetail.do?quitButtonDestination=BusinessEntityResults&nameTyp=ENT&masterFileId={best_id}&entityId2={best_id}&fileId={best_file}&srchTyp=ENTITY"
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(0.5)
    
    detail_text = page.inner_text('body')
    
    # Parse detail
    import re
    result = {}
    
    name_m = re.search(r'Name\t(.+?)(?:\n|Status)', detail_text)
    result['entity_name'] = name_m.group(1).strip() if name_m else ''
    
    status_m = re.search(r'Status\t(.+?)(?:\t|Formation)', detail_text)
    result['status'] = status_m.group(1).strip() if status_m else ''
    
    id_m = re.search(r'ID number\t(\d+)', detail_text)
    result['entity_id'] = id_m.group(1) if id_m else best_id
    
    addr_m = re.search(r'Principal office street address\t(.+?)(?:\n|Principal office mailing)', detail_text)
    result['address'] = addr_m.group(1).strip() if addr_m else ''
    
    agent_m = re.search(r'Registered Agent\nName\t(.+?)(?:\n|Street)', detail_text)
    result['agent'] = agent_m.group(1).strip() if agent_m else ''
    
    return result

def main():
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for store_ids, search_term, expected in SEARCHES:
            try:
                result = search_co_sos(page, search_term, expected)
                if result and 'error' not in result:
                    results[search_term] = result
                    print(f"✓ {search_term}: {result.get('entity_name','')} -> Agent: {result.get('agent','')}")
                else:
                    results[search_term] = result
                    print(f"✗ {search_term}: {result}")
                
                # Save results periodically
                if len(results) % 5 == 0:
                    with open('co_sos_results.json', 'w') as f:
                        json.dump(results, f, indent=2)
                    
            except Exception as e:
                print(f"✗ {search_term}: ERROR - {e}")
                results[search_term] = {"error": str(e)}
        
        browser.close()
    
    # Save final results
    with open('co_sos_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Update the main progress file
    with open('mw_owner_progress.json') as f:
        data = json.load(f)
    
    count = 0
    for store_ids_list, search_term, _ in SEARCHES:
        if search_term in results and 'error' not in results[search_term]:
            r = results[search_term]
            for sid in store_ids_list:
                if sid in data and data[sid]['status'] == 'needs_manual':
                    data[sid].update({
                        'owner_name': r.get('agent', ''),
                        'registered_agent': r.get('agent', ''),
                        'principal_address': r.get('address', ''),
                        'business_entity': f"{r.get('entity_name', '')} (CO Corp, ID {r.get('entity_id', '')})",
                        'source': 'CO Secretary of State',
                        'status': 'found'
                    })
                    count += 1
    
    with open('mw_owner_progress.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    remaining = sum(1 for v in data.values() if v.get('status') == 'needs_manual')
    print(f"\nUpdated {count} stores. Remaining: {remaining}")

if __name__ == '__main__':
    main()
