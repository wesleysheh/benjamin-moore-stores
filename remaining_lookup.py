#!/usr/bin/env python3
"""Look up remaining CO store owners via CO SOS."""
import json
import re
import time
from playwright.sync_api import sync_playwright

CO_SEARCHES = [
    (["10015646"], "steve's paint", "STEVE"),
    (["10021993"], "lamar bms", "LAMAR"),
]

def search_co_sos(page, search_term, expected_fragment):
    page.goto("https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do?resetTransTyp=Y",
              wait_until="networkidle", timeout=15000)
    
    entity_input = page.query_selector('input[name="searchName"]')
    if not entity_input:
        return {"error": "No searchName input"}
    
    entity_input.fill(search_term)
    
    submit = page.query_selector('input[type="submit"][name="cmd"]')
    if submit:
        submit.click()
    else:
        entity_input.press("Enter")
    
    page.wait_for_load_state("networkidle", timeout=10000)
    text = page.inner_text('body')
    
    if 'No records found' in text:
        return {"error": f"No records for {search_term}"}
    
    lines = text.split('\n')
    best_id = None
    for line in lines:
        if expected_fragment.upper() in line.upper():
            if 'Good Standing' in line:
                parts = line.strip().split('\t')
                for p in parts:
                    if p.strip().isdigit() and len(p.strip()) > 8:
                        best_id = p.strip()
                        break
                if best_id:
                    break
    
    if not best_id:
        for line in lines:
            if expected_fragment.upper() in line.upper():
                parts = line.strip().split('\t')
                for p in parts:
                    if p.strip().isdigit() and len(p.strip()) > 8:
                        best_id = p.strip()
                        break
                if best_id:
                    break
    
    if not best_id:
        return {"error": f"No entity ID. Results: {text[:500]}"}
    
    url = f"https://www.sos.state.co.us/biz/BusinessEntityDetail.do?quitButtonDestination=BusinessEntityResults&nameTyp=ENT&masterFileId={best_id}&entityId2={best_id}&fileId={best_id}&srchTyp=ENTITY"
    page.goto(url, wait_until="networkidle", timeout=10000)
    detail_text = page.inner_text('body')
    
    if 'Details' not in detail_text:
        url2 = f"https://www.sos.state.co.us/biz/TradeNameSummary.do?quitButtonDestination=BusinessEntityResults&nameTyp=TRDNM&masterFileId={best_id}&entityId2={best_id}&fileId={best_id}&srchTyp=TRDNM"
        page.goto(url2, wait_until="networkidle", timeout=10000)
        detail_text = page.inner_text('body')
    
    result = {}
    name_m = re.search(r'Name\t(.+?)(?:\n|$)', detail_text)
    result['entity_name'] = name_m.group(1).strip() if name_m else ''
    
    agent_m = re.search(r'Registered Agent\nName\t(.+?)(?:\n|$)', detail_text)
    if not agent_m:
        agent_m = re.search(r'Registrant name\n(.+?)(?:\n|$)', detail_text)
    result['agent'] = agent_m.group(1).strip() if agent_m else ''
    
    addr_m = re.search(r'Principal office street address\t(.+?)(?:\n|$)', detail_text)
    result['address'] = addr_m.group(1).strip() if addr_m else ''
    
    id_m = re.search(r'ID number\t(\d+)', detail_text)
    result['entity_id'] = id_m.group(1) if id_m else best_id
    
    return result

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        with open('mw_owner_progress.json') as f:
            data = json.load(f)
        
        for store_ids, search_term, expected in CO_SEARCHES:
            try:
                result = search_co_sos(page, search_term, expected)
                if 'error' not in result:
                    print(f"✓ {search_term}: {result.get('entity_name','')} -> Agent: {result.get('agent','')}")
                    for sid in store_ids:
                        if sid in data:
                            data[sid].update({
                                'owner_name': result.get('agent', ''),
                                'registered_agent': result.get('agent', ''),
                                'principal_address': result.get('address', ''),
                                'business_entity': f"{result.get('entity_name', '')} (CO, ID {result.get('entity_id', '')})",
                                'source': 'CO Secretary of State',
                                'status': 'found'
                            })
                            print(f"  Updated {sid}")
                else:
                    print(f"✗ {search_term}: {result['error'][:150]}")
            except Exception as e:
                print(f"✗ {search_term}: {e}")
            time.sleep(2)
        
        browser.close()
    
    with open('mw_owner_progress.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    main()
