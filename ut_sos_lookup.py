#!/usr/bin/env python3
"""Batch UT business entity lookup using Playwright."""
import json
import re
import time
from playwright.sync_api import sync_playwright

# Utah stores needing lookup
SEARCHES = [
    (["10001934"], "park city paint", "PARK CITY PAINT"),
    (["10002526"], "weber paint", "WEBER PAINT"),
    (["10002698"], "wilson paint", "WILSON"),
    (["10004654"], "salt lake paint", "SALT LAKE PAINT"),
    (["10006195"], "bennett paint", "BENNETT PAINT"),
    (["10008359"], "layton true value", "LAYTON TRUE VALUE"),
    (["10008429"], "springville true value", "SPRINGVILLE TRUE VALUE"),
    (["10009662"], "sandy paint", "SANDY PAINT"),
    (["10009670"], "rocky mountain paint", "ROCKY MOUNTAIN PAINT"),
    (["10011047"], "plain city true value", "PLAIN CITY TRUE VALUE"),
    (["10011614"], "farmington paint", "FARMINGTON PAINT"),
    (["10013016"], "fishlake lumber", "FISHLAKE"),
    (["10017894"], "rocky mountain paint", "ROCKY MOUNTAIN PAINT"),
    (["10019286"], "rocky mountain paint", "ROCKY MOUNTAIN PAINT"),
]

def search_ut_sos(page, search_term, expected_fragment):
    """Search Utah business entity database."""
    url = f"https://secure.utah.gov/bes/index.html"
    page.goto(url, wait_until="networkidle", timeout=20000)
    time.sleep(1)
    
    # Fill search
    search_input = page.query_selector('input[name="busName"]') or page.query_selector('input#busName')
    if not search_input:
        # Try to find any text input
        inputs = page.query_selector_all('input[type="text"]')
        if inputs:
            search_input = inputs[0]
        else:
            return {"error": f"No search input found on UT SOS page"}
    
    search_input.fill(search_term)
    
    # Submit
    submit = page.query_selector('input[type="submit"]') or page.query_selector('button[type="submit"]')
    if submit:
        submit.click()
    else:
        search_input.press("Enter")
    
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(1)
    
    text = page.inner_text('body')
    
    # Look for matching entity links
    links = page.query_selector_all('a')
    best_link = None
    for link in links:
        link_text = (link.inner_text() or '').upper()
        if expected_fragment.upper() in link_text:
            href = link.get_attribute('href') or ''
            if 'bes' in href.lower() or 'detail' in href.lower() or 'entity' in href.lower():
                best_link = link
                break
    
    if not best_link:
        # Try clicking any matching text link
        for link in links:
            link_text = (link.inner_text() or '').upper()
            if expected_fragment.split()[0] in link_text and len(link_text) > 3:
                best_link = link
                break
    
    if best_link:
        best_link.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(1)
        detail_text = page.inner_text('body')
    else:
        detail_text = text
    
    result = {'raw': detail_text[:2000]}
    
    # Try to extract owner/agent info
    for pattern in [r'Registered Agent[:\s]+(.+?)(?:\n|$)', r'Agent[:\s]+(.+?)(?:\n|$)',
                    r'Principal[:\s]+(.+?)(?:\n|$)', r'Owner[:\s]+(.+?)(?:\n|$)']:
        m = re.search(pattern, detail_text, re.IGNORECASE)
        if m:
            result['agent'] = m.group(1).strip()
            break
    
    return result


def main():
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for store_ids, search_term, expected in SEARCHES:
            try:
                result = search_ut_sos(page, search_term, expected)
                results[search_term] = result
                if 'agent' in result:
                    print(f"✓ {search_term}: Agent={result['agent']}")
                else:
                    raw_preview = result.get('raw', '')[:150]
                    print(f"? {search_term}: {raw_preview}")
            except Exception as e:
                print(f"✗ {search_term}: {e}")
                results[search_term] = {"error": str(e)}
            time.sleep(2)
        
        browser.close()
    
    with open('ut_sos_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDone. Results in ut_sos_results.json")

if __name__ == '__main__':
    main()
