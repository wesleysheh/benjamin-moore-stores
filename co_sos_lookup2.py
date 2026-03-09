#!/usr/bin/env python3
"""Batch CO SOS entity lookup using Playwright - fixed form submission."""
import json
import re
import time
from playwright.sync_api import sync_playwright

SEARCHES = [
    (["10004865"], "manweiler hardware", "MANWEILER HARDWARE"),
    (["10001224"], "wylie", "WYLIE"),
    (["10002722"], "park supply", "PARK SUPPLY"),
    (["10003533"], "wray lumber", "WRAY LUMBER"),
    (["10003839"], "poncha lumber", "PONCHA"),
    (["10004023"], "mountain high paint", "MOUNTAIN HIGH"),
    (["10006322"], "collbran supply", "COLLBRAN"),
    (["10006789"], "mountain color", "MOUNTAIN COLOR"),
    (["10006839"], "northside paint", "NORTHSIDE"),
    (["10006980"], "arkansas valley", "ARKANSAS"),
    (["10009824"], "noco paint", "NOCO"),
    (["10010512"], "g4 coatings", "G4"),
    (["10011128"], "juniper", "JUNIPER"),
    (["10012449"], "ajax supply", "AJAX"),
    (["10012697"], "arvada flooring", "ARVADA"),
    (["10013065"], "herman lumber", "HERMAN"),
    (["10013129"], "la junta trading", "LA JUNTA"),
    (["10013163"], "pandhandle", "PANDHANDLE"),
    (["10013336"], "stratton equity", "STRATTON"),
    (["10013825"], "pronghorn", "PRONGHORN"),
    (["10014576"], "choice building", "CHOICE"),
    (["10014582"], "delta hardware", "DELTA HARDWARE"),
    (["10014639"], "valley hardware meeker", "VALLEY HARDWARE"),
    (["10015646"], "steve paint", "STEVE"),
    (["10016432"], "agfinity", "AGFINITY"),
    (["10016433"], "poudre valley", "POUDRE VALLEY"),
    (["10017578"], "aguilar", "AGUILAR"),
    (["10018256"], "m m decorating", "DECORATING"),
    (["10019644"], "colored red", "COLORED RED"),
    (["10021008"], "budget home", "BUDGET HOME"),
    (["10021558"], "paint pallet", "PAINT PALLET"),
    (["10021993"], "lamar bms", "LAMAR BMS"),
    (["10000481"], "colors durango", "COLORS"),
    (["10002922"], "home store", "HOME STORE"),
]

def search_co_sos(page, search_term, expected_fragment):
    """Search CO SOS using the proper search form."""
    # Navigate to search criteria page
    page.goto("https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do?resetTransTyp=Y", 
              wait_until="networkidle", timeout=15000)
    
    # Find the entity name input specifically
    # The form has an input named 'entityName'
    entity_input = page.query_selector('input[name="entityName"]')
    if not entity_input:
        # Try alternate selectors
        entity_input = page.query_selector('#entityName')
        if not entity_input:
            # Get all inputs and their names
            inputs = page.query_selector_all('input')
            input_names = []
            for inp in inputs:
                name = inp.get_attribute('name') or ''
                input_type = inp.get_attribute('type') or ''
                input_names.append(f"{name}:{input_type}")
            return {"error": f"No entityName input found. Inputs: {input_names}"}
    
    entity_input.fill(search_term)
    
    # Click the search/submit button
    submit = page.query_selector('input[type="submit"][value*="Search"]')
    if not submit:
        submit = page.query_selector('input[type="submit"]')
    if not submit:
        submit = page.query_selector('button[type="submit"]')
    
    if submit:
        submit.click()
    else:
        # Try form submit
        entity_input.press("Enter")
    
    page.wait_for_load_state("networkidle", timeout=10000)
    
    text = page.inner_text('body')
    
    # Check if we got search results
    if 'matching record' not in text and 'No records found' not in text:
        return {"error": f"Unexpected page after search: {text[:300]}"}
    
    if 'No records found' in text:
        return {"error": f"No records found for {search_term}"}
    
    # Find Good Standing entities matching expected fragment
    lines = text.split('\n')
    best_id = None
    best_file = None
    
    for line in lines:
        if expected_fragment.upper() in line.upper():
            if 'Good Standing' in line:
                parts = line.strip().split('\t')
                for i, p in enumerate(parts):
                    if p.strip().isdigit() and len(p.strip()) > 8:
                        best_id = p.strip()
                        if i+1 < len(parts) and parts[i+1].strip().isdigit():
                            best_file = parts[i+1].strip()
                        else:
                            best_file = best_id
                        break
                if best_id:
                    break
    
    if not best_id:
        # Try Effective or any matching
        for line in lines:
            if expected_fragment.upper() in line.upper():
                parts = line.strip().split('\t')
                for i, p in enumerate(parts):
                    p_clean = p.strip()
                    if p_clean.isdigit() and len(p_clean) > 8:
                        best_id = p_clean
                        if i+1 < len(parts) and parts[i+1].strip().isdigit():
                            best_file = parts[i+1].strip()
                        else:
                            best_file = best_id
                        break
                if best_id:
                    break
    
    if not best_id:
        return {"error": f"No entity ID found for {search_term}. Results: {text[:500]}"}
    
    # Navigate to entity detail
    url = f"https://www.sos.state.co.us/biz/BusinessEntityDetail.do?quitButtonDestination=BusinessEntityResults&nameTyp=ENT&masterFileId={best_id}&entityId2={best_id}&fileId={best_file}&srchTyp=ENTITY"
    page.goto(url, wait_until="networkidle", timeout=10000)
    
    detail_text = page.inner_text('body')
    
    # Check if it's a trade name - might redirect differently
    if 'Details' not in detail_text:
        # Try trade name summary
        url2 = f"https://www.sos.state.co.us/biz/TradeNameSummary.do?quitButtonDestination=BusinessEntityResults&nameTyp=TRDNM&masterFileId={best_id}&entityId2={best_id}&fileId={best_file}&srchTyp=TRDNM"
        page.goto(url2, wait_until="networkidle", timeout=10000)
        detail_text = page.inner_text('body')
    
    result = {}
    
    name_m = re.search(r'Name\t(.+?)(?:\n|$)', detail_text)
    result['entity_name'] = name_m.group(1).strip() if name_m else ''
    
    status_m = re.search(r'Status\t(.+?)(?:\t|$)', detail_text)
    result['status'] = status_m.group(1).strip() if status_m else ''
    
    id_m = re.search(r'ID number\t(\d+)', detail_text)
    result['entity_id'] = id_m.group(1) if id_m else best_id
    
    addr_m = re.search(r'Principal office street address\t(.+?)(?:\n|$)', detail_text)
    result['address'] = addr_m.group(1).strip() if addr_m else ''
    
    agent_m = re.search(r'Registered Agent\nName\t(.+?)(?:\n|$)', detail_text)
    if not agent_m:
        agent_m = re.search(r'Registrant name\n(.+?)(?:\n|$)', detail_text)
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
                    err = result.get('error', 'unknown') if result else 'None'
                    print(f"✗ {search_term}: {err[:100]}")
                    
            except Exception as e:
                print(f"✗ {search_term}: ERROR - {e}")
                results[search_term] = {"error": str(e)}
        
        browser.close()
    
    # Save results
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
                    print(f"  Updated {sid}: {data[sid]['name']}")
    
    with open('mw_owner_progress.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    remaining = sum(1 for v in data.values() if v.get('status') == 'needs_manual')
    print(f"\nUpdated {count} stores. Remaining: {remaining}")

if __name__ == '__main__':
    main()
