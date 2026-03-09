#!/usr/bin/env python3
"""Automated SOS lookup using Playwright. Grinds through all states."""
import json, sys, time, re
from playwright.sync_api import sync_playwright

PROGRESS_FILE = 'mw_owner_progress.json'

def load_progress():
    with open(PROGRESS_FILE) as f:
        return json.load(f)

def save_progress(data):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def update_store(data, store_id, owner_name='', agent='', address='', entity='', source='', status='found'):
    data[store_id]['owner_name'] = owner_name
    data[store_id]['registered_agent'] = agent
    data[store_id]['principal_address'] = address
    data[store_id]['business_entity'] = entity
    data[store_id]['source'] = source
    data[store_id]['status'] = status
    save_progress(data)

def search_nv(page, name):
    """Search Nevada SOS"""
    page.goto('https://esos.nv.gov/EntitySearch/OnlineEntitySearch', timeout=30000)
    page.wait_for_load_state('networkidle')
    
    # Select Contains
    page.click('input[value="Contains"]')
    # Type name
    page.fill('input[name="EntityName"]', name)
    # Search
    page.click('input[value="Search"]')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # Check for alert (no results)
    alert = page.query_selector('.modal-body')
    if alert and 'No records found' in (alert.text_content() or ''):
        return None
    
    # Look for results table
    results = page.query_selector_all('table.table tbody tr')
    if not results:
        return None
    
    # Click first result
    first_link = page.query_selector('table.table tbody tr td a')
    if first_link:
        first_link.click()
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        
        # Extract details
        content = page.content()
        return content
    return None

def search_co(page, name):
    """Search Colorado SOS"""
    page.goto('https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do', timeout=30000)
    page.wait_for_load_state('networkidle')
    
    page.fill('#entityName', name)
    page.click('input[value="Search"]')
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    # Click first result
    first_link = page.query_selector('table.resultsTable tbody tr td a')
    if first_link:
        first_link.click()
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        return page.content()
    return None

def search_nm(page, name):
    """Search New Mexico SOS"""
    page.goto('https://portal.sos.state.nm.us/BFS/online/CorporationBusinessSearch', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    search_input = page.query_selector('input[type="text"]')
    if search_input:
        search_input.fill(name)
        page.keyboard.press('Enter')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        first_link = page.query_selector('a[href*="CorporationBusinessInformation"]')
        if first_link:
            first_link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            return page.content()
    return None

def search_az(page, name):
    """Search Arizona Corporation Commission"""
    page.goto('https://ecorp.azcc.gov/EntitySearch/Index', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    page.fill('#Name', name)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    first_link = page.query_selector('a[href*="EntityDetail"]')
    if first_link:
        first_link.click()
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        return page.content()
    return None

def search_wy(page, name):
    """Search Wyoming SOS"""
    page.goto(f'https://wyobiz.wyo.gov/Business/FilingSearch.aspx', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    search_input = page.query_selector('#MainContent_txtFilingName')
    if search_input:
        search_input.fill(name)
        page.click('#MainContent_cmdSearch')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        first_link = page.query_selector('a[id*="lnkBusiness"]')
        if first_link:
            first_link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            return page.content()
    return None

def search_mt(page, name):
    """Search Montana SOS"""
    page.goto(f'https://biz.sosmt.gov/search/business', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    search_input = page.query_selector('input[type="search"], input[type="text"]')
    if search_input:
        search_input.fill(name)
        page.keyboard.press('Enter')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        first_link = page.query_selector('a[href*="business/"]')
        if first_link:
            first_link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            return page.content()
    return None

def search_ut(page, name):
    """Search Utah Division of Corporations"""
    page.goto(f'https://secure.utah.gov/bes/index.html', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    search_input = page.query_selector('#SearchBox, input[type="text"]')
    if search_input:
        search_input.fill(name)
        page.keyboard.press('Enter')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        return page.content()
    return None

def search_id(page, name):
    """Search Idaho SOS"""
    page.goto('https://sosbiz.idaho.gov/search/business', timeout=30000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    search_input = page.query_selector('input[type="text"]')
    if search_input:
        search_input.fill(name)
        page.keyboard.press('Enter')
        page.wait_for_load_state('networkidle')
        time.sleep(2)
        
        first_link = page.query_selector('a[href*="business/"]')
        if first_link:
            first_link.click()
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            return page.content()
    return None

def extract_officers_from_html(html):
    """Try to extract officer/owner info from page HTML"""
    # Common patterns across SOS sites
    info = {}
    
    # Look for officer/manager/member names
    officer_patterns = [
        r'(?:President|Owner|Manager|Managing Member|Principal|Director|CEO|Officer|Organizer)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:Registered Agent)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]
    
    for pattern in officer_patterns:
        matches = re.findall(pattern, html, re.I)
        if matches:
            info['officers'] = matches
    
    return info

SEARCH_FUNCS = {
    'NV': search_nv,
    'CO': search_co,
    'NM': search_nm,
    'AZ': search_az,
    'WY': search_wy,
    'MT': search_mt,
    'UT': search_ut,
    'ID': search_id,
}

def main():
    state = sys.argv[1] if len(sys.argv) > 1 else None
    data = load_progress()
    
    # Get stores needing lookup
    needs = [(k, v) for k, v in data.items() if v['status'] == 'needs_manual']
    if state:
        needs = [(k, v) for k, v in needs if v['state'] == state]
    
    print(f"Processing {len(needs)} stores" + (f" in {state}" if state else ""))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        for i, (store_id, store) in enumerate(needs):
            st = store['state']
            name = store['name']
            search_fn = SEARCH_FUNCS.get(st)
            
            if not search_fn:
                print(f"[{i+1}/{len(needs)}] SKIP {name} ({st}) - no search function")
                continue
            
            # Simplify name for search
            search_name = name.replace(' - ', ' ').replace('-', ' ')
            # Remove suffixes like INC, LLC, etc for broader search
            search_name_clean = re.sub(r'\b(INC\.?|LLC\.?|CO\.?|CORP\.?|LTD\.?)\b', '', search_name).strip()
            
            print(f"[{i+1}/{len(needs)}] Searching {st} SOS for: {name} (query: {search_name_clean})")
            
            try:
                html = search_fn(page, search_name_clean)
                if html:
                    # Save raw HTML for parsing
                    with open(f'/tmp/sos_{store_id}.html', 'w') as f:
                        f.write(html)
                    print(f"  → Got results page ({len(html)} chars)")
                    
                    # Try to extract info
                    info = extract_officers_from_html(html)
                    if info.get('officers'):
                        print(f"  → Officers: {info['officers']}")
                else:
                    print(f"  → No results found")
                    update_store(data, store_id, status='not_found', source=f'{st} SOS')
            except Exception as e:
                print(f"  → Error: {e}")
            
            time.sleep(1)  # Be polite
        
        browser.close()

if __name__ == '__main__':
    main()
