#!/usr/bin/env python3
"""Automated SOS lookup v2 - state by state grinder for BM store owners."""
import json, sys, time, re, os

PROGRESS_FILE = 'mw_owner_progress.json'

def load_progress():
    with open(PROGRESS_FILE) as f:
        return json.load(f)

def save_progress(data):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def search_co(page, name):
    """Colorado SOS"""
    page.goto('https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    page.fill('#searchCriteria', name)
    page.click('input[value="Search"]')
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    # Find entity detail links
    links = page.query_selector_all('a[href*="BusinessEntityDetail"]')
    if not links:
        return None, None
    
    # Click first entity
    links[0].click()
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

def search_ut(page, name):
    """Utah Division of Corporations"""
    page.goto('https://secure.utah.gov/bes/index.html', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    # Utah uses an Angular app
    inp = page.query_selector('input[type="text"], input[type="search"]')
    if not inp:
        return None, None
    inp.fill(name)
    
    # Find search button
    btn = page.query_selector('button.btn-primary, button[type="submit"], input[type="submit"]')
    if btn:
        btn.click()
    else:
        page.keyboard.press('Enter')
    
    page.wait_for_load_state('networkidle')
    time.sleep(3)
    
    # Click first result
    link = page.query_selector('a[href*="detail"], a[href*="Details"], tr.clickable, table tbody tr a')
    if link:
        link.click()
        page.wait_for_load_state('networkidle')
        time.sleep(2)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

def search_mt(page, name):
    """Montana SOS"""
    page.goto('https://biz.sosmt.gov/search/business', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    inp = page.query_selector('input[type="text"], input[type="search"]')
    if not inp:
        return None, None
    inp.fill(name)
    page.keyboard.press('Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3)
    
    link = page.query_selector('a[href*="/business/"]')
    if not link:
        return None, None
    
    link.click()
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

def search_wy(page, name):
    """Wyoming SOS"""
    page.goto('https://wyobiz.wyo.gov/Business/FilingSearch.aspx', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    inp = page.query_selector('#MainContent_txtFilingName')
    if not inp:
        return None, None
    inp.fill(name)
    
    btn = page.query_selector('#MainContent_cmdSearch')
    if btn:
        btn.click()
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    link = page.query_selector('a[id*="lnkBusiness"]')
    if not link:
        return None, None
    
    link.click()
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

def search_az(page, name):
    """Arizona Corporation Commission"""
    page.goto('https://ecorp.azcc.gov/EntitySearch/Index', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    inp = page.query_selector('#Name')
    if not inp:
        return None, None
    inp.fill(name)
    
    btn = page.query_selector('button[type="submit"], input[type="submit"]')
    if btn:
        btn.click()
    page.wait_for_load_state('networkidle')
    time.sleep(3)
    
    link = page.query_selector('a[href*="EntityDetail"]')
    if not link:
        return None, None
    
    link.click()
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

def search_nm(page, name):
    """New Mexico SOS"""
    page.goto('https://portal.sos.state.nm.us/BFS/online/CorporationBusinessSearch', timeout=15000)
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    inp = page.query_selector('input[type="text"]')
    if not inp:
        return None, None
    inp.fill(name)
    page.keyboard.press('Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3)
    
    link = page.query_selector('a[href*="CorporationBusinessInformation"]')
    if not link:
        return None, None
    
    link.click()
    page.wait_for_load_state('networkidle')
    time.sleep(2)
    
    text = page.inner_text('body')
    html = page.content()
    return text, html

SEARCH_FUNCS = {
    'CO': search_co,
    'UT': search_ut,
    'MT': search_mt,
    'WY': search_wy,
    'AZ': search_az,
    'NM': search_nm,
}

def extract_info(text, state):
    """Extract owner/agent info from page text."""
    if not text:
        return {}
    
    info = {
        'owner_name': '',
        'registered_agent': '',
        'principal_address': '',
        'business_entity': '',
    }
    
    lines = text.split('\n')
    
    # Try to find registered agent
    for i, line in enumerate(lines):
        line_l = line.strip().lower()
        if 'registered agent' in line_l or 'agent name' in line_l:
            # Next non-empty line is usually the agent
            for j in range(i+1, min(i+5, len(lines))):
                val = lines[j].strip()
                if val and len(val) > 2 and val.lower() not in ['name', 'address', 'city', 'state', 'zip']:
                    info['registered_agent'] = val
                    break
    
    # Try to find principal/owner/officer
    officer_keywords = ['president', 'owner', 'managing member', 'manager', 'ceo', 'principal', 'officer', 'director', 'organizer', 'member']
    officers = []
    for i, line in enumerate(lines):
        line_l = line.strip().lower()
        for kw in officer_keywords:
            if kw in line_l:
                # Could be "President: John Smith" or the name on the next line
                parts = line.strip().split(':')
                if len(parts) >= 2 and len(parts[1].strip()) > 2:
                    officers.append(f"{parts[1].strip()} ({parts[0].strip()})")
                elif i+1 < len(lines) and len(lines[i+1].strip()) > 2:
                    name_candidate = lines[i+1].strip()
                    if name_candidate.lower() not in officer_keywords and len(name_candidate) < 80:
                        officers.append(f"{name_candidate} ({line.strip()})")
                break
    
    if officers:
        info['owner_name'] = ', '.join(officers[:5])
    
    # Try to find entity name
    for i, line in enumerate(lines):
        line_l = line.strip().lower()
        if 'entity name' in line_l or 'business name' in line_l or 'filing name' in line_l:
            for j in range(i+1, min(i+3, len(lines))):
                val = lines[j].strip()
                if val and len(val) > 2:
                    info['business_entity'] = val
                    break
    
    # Principal address
    for i, line in enumerate(lines):
        line_l = line.strip().lower()
        if 'principal' in line_l and 'address' in line_l:
            addr_parts = []
            for j in range(i+1, min(i+5, len(lines))):
                val = lines[j].strip()
                if val and len(val) > 2 and len(val) < 100:
                    addr_parts.append(val)
                else:
                    break
            if addr_parts:
                info['principal_address'] = ', '.join(addr_parts)
            break
    
    return info

def clean_search_name(name):
    """Clean store name for SOS search."""
    # Remove common suffixes
    name = re.sub(r'\s*[-–]\s*(CHERRY|PARKER|CENTENNIAL|LITTLETON|LAKEWOOD|FORT COLL.*|BOULDER|DENVER.*|WESTMIN.*|HIGHLAN.*|LONGMON.*|EVANS|LOVELAND)$', '', name, flags=re.I)
    name = re.sub(r'\b(INC\.?|LLC\.?|CO\.?|CORP\.?|LTD\.?|L\.?L\.?C\.?)\s*$', '', name, flags=re.I).strip()
    name = re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()
    # Remove trailing punctuation
    name = name.rstrip('.,- ')
    return name

def main():
    state = sys.argv[1] if len(sys.argv) > 1 else None
    if not state:
        print("Usage: python3 sos_grinder2.py <STATE>")
        sys.exit(1)
    
    if state not in SEARCH_FUNCS:
        print(f"No search function for {state}. Available: {', '.join(SEARCH_FUNCS.keys())}")
        sys.exit(1)
    
    data = load_progress()
    needs = [(k, v) for k, v in data.items() if isinstance(v, dict) and v.get('status') == 'needs_manual' and v.get('state') == state]
    
    print(f"=== Processing {len(needs)} stores in {state} ===", flush=True)
    
    from playwright.sync_api import sync_playwright
    
    found_count = 0
    not_found_count = 0
    error_count = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        search_fn = SEARCH_FUNCS[state]
        
        for i, (store_id, store) in enumerate(needs):
            name = store['name']
            search_name = clean_search_name(name)
            
            print(f"[{i+1}/{len(needs)}] {name} -> query: '{search_name}'", flush=True)
            
            try:
                text, html = search_fn(page, search_name)
                
                if text:
                    info = extract_info(text, state)
                    
                    has_data = any(info.get(k) for k in ['owner_name', 'registered_agent', 'business_entity'])
                    
                    if has_data:
                        data[store_id]['owner_name'] = info.get('owner_name', '')
                        data[store_id]['registered_agent'] = info.get('registered_agent', '')
                        data[store_id]['principal_address'] = info.get('principal_address', '')
                        data[store_id]['business_entity'] = info.get('business_entity', '')
                        data[store_id]['source'] = f'{state} SOS'
                        data[store_id]['status'] = 'found'
                        found_count += 1
                        print(f"  ✅ Found: agent={info.get('registered_agent','?')}, owner={info.get('owner_name','?')[:50]}", flush=True)
                    else:
                        # Got a page but couldn't extract useful info - save HTML for review
                        with open(f'/tmp/sos_{store_id}.html', 'w') as f:
                            f.write(html)
                        with open(f'/tmp/sos_{store_id}.txt', 'w') as f:
                            f.write(text)
                        data[store_id]['source'] = f'{state} SOS (needs parse)'
                        data[store_id]['status'] = 'needs_parse'
                        print(f"  ⚠️  Got page but couldn't parse - saved to /tmp/sos_{store_id}.txt", flush=True)
                else:
                    data[store_id]['source'] = f'{state} SOS'
                    data[store_id]['status'] = 'not_found'
                    not_found_count += 1
                    print(f"  ❌ Not found", flush=True)
                
                save_progress(data)
                
            except Exception as e:
                error_count += 1
                print(f"  💥 Error: {str(e)[:80]}", flush=True)
            
            time.sleep(1.5)  # Be polite
        
        browser.close()
    
    print(f"\n=== {state} Complete ===", flush=True)
    print(f"Found: {found_count}, Not found: {not_found_count}, Errors: {error_count}", flush=True)

if __name__ == '__main__':
    main()
