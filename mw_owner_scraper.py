import urllib.request
import urllib.parse
import json
import time
import ssl
import csv
import os
import re

PROGRESS_FILE = "/Users/clawbox-1/.openclaw/workspace/mw_owner_progress.json"
OUTPUT_CSV = "/Users/clawbox-1/.openclaw/workspace/mw_store_owners.csv"
ctx = ssl.create_default_context()

# State SOS API endpoints (same platform: Idaho, North Dakota use this)
# States with working JSON APIs
STATE_APIS = {
    "ID": {
        "search": "https://sosbiz.idaho.gov/api/Records/businesssearch",
        "detail": "https://sosbiz.idaho.gov/api/FilingDetail/business/{id}/false"
    },
    "ND": {
        "search": "https://firststop.sos.nd.gov/api/Records/businesssearch",
        "detail": "https://firststop.sos.nd.gov/api/FilingDetail/business/{id}/false"
    },
}

# For states without working APIs, we'll note them for manual/web lookup

def api_search(state, name):
    """Search state business registry"""
    if state not in STATE_APIS:
        return None
    
    api = STATE_APIS[state]
    # Try different search variations
    search_names = [name]
    # Clean up name variations
    clean = re.sub(r'\s+(INC|LLC|CO|CORP|COMPANY|LTD)\.?\s*$', '', name, flags=re.I).strip()
    if clean != name:
        search_names.append(clean)
    # Try first two words
    words = name.split()
    if len(words) >= 2:
        search_names.append(f"{words[0]} {words[1]}")
    
    for search_name in search_names:
        try:
            payload = json.dumps({
                "SEARCH_VALUE": search_name,
                "STARTS_WITH_YN": "true",
                "ACTIVE_ONLY_YN": "true"
            }).encode()
            req = urllib.request.Request(api["search"], data=payload, 
                                         headers={"Content-Type": "application/json", "Accept": "application/json"})
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = json.loads(resp.read())
            
            rows = data.get("rows", {})
            if rows:
                # Return the first active result
                for rid, info in rows.items():
                    return {"id": info.get("ID"), "title": info.get("TITLE", [""]), 
                            "agent": info.get("AGENT", ""), "status": info.get("STATUS", ""),
                            "state": state, "search_name": search_name}
        except Exception as e:
            continue
    return None

def api_detail(state, record_id):
    """Get business detail from state registry"""
    if state not in STATE_APIS:
        return None
    api = STATE_APIS[state]
    try:
        url = api["detail"].format(id=record_id)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
        
        result = {}
        for item in data.get("DRAWER_DETAIL_LIST", []):
            label = item.get("LABEL", "")
            value = item.get("VALUE", "") or ""
            if label == "Principal Address":
                result["principal"] = value
            elif label == "Mailing Address":
                result["mailing"] = value
            elif label == "Registered Agent":
                result["agent"] = value
            elif label == "Formed In":
                result["formed_in"] = value
        return result
    except Exception as e:
        return None

def web_search_owner(store_name, city, state):
    """Fallback: try to find owner via web search description"""
    # We'll mark these for manual lookup
    return None

# Load stores
with open("/Users/clawbox-1/.openclaw/workspace/mw_stores.json") as f:
    stores = json.load(f)

# Load progress
progress = {}
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE) as f:
        progress = json.load(f)

print(f"Loaded {len(stores)} stores, {len(progress)} already processed", flush=True)

results = []
new_count = 0
for i, store in enumerate(stores):
    key = store["store_number"]
    
    if key in progress:
        results.append(progress[key])
        continue
    
    result = {
        "store_number": store["store_number"],
        "name": store["name"],
        "city": store["city"],
        "state": store["state"],
        "phone": store["phone"],
        "email": store["email"],
        "owner_name": "",
        "registered_agent": "",
        "principal_address": "",
        "business_entity": "",
        "source": "",
        "status": "not_found"
    }
    
    if store["state"] in STATE_APIS:
        search_result = api_search(store["state"], store["name"])
        if search_result:
            detail = api_detail(store["state"], search_result["id"])
            if detail:
                # Extract owner name from principal address (usually first line)
                principal = detail.get("principal", "")
                owner = principal.split("\n")[0] if principal else ""
                agent = detail.get("agent", "")
                agent_name = ""
                if agent:
                    lines = agent.split("\n")
                    # Skip "Noncommercial" or ID numbers
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("0") and line.lower() != "noncommercial" and line.lower() != "commercial":
                            agent_name = line
                            break
                
                result["owner_name"] = owner
                result["registered_agent"] = agent_name
                result["principal_address"] = principal.replace("\n", ", ")
                result["business_entity"] = search_result["title"][0] if search_result["title"] else ""
                result["source"] = f"{store['state']} SOS"
                result["status"] = "found"
            else:
                result["business_entity"] = search_result["title"][0] if search_result["title"] else ""
                result["registered_agent"] = search_result.get("agent", "")
                result["source"] = f"{store['state']} SOS (search only)"
                result["status"] = "partial"
        else:
            result["source"] = f"{store['state']} SOS (no match)"
            result["status"] = "no_match"
    else:
        result["source"] = "no_api"
        result["status"] = "needs_manual"
    
    progress[key] = result
    results.append(result)
    new_count += 1
    
    if new_count % 5 == 0:
        # Save progress
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    
    if new_count % 10 == 0:
        print(f"Progress: {i+1}/{len(stores)} | Found: {sum(1 for r in results if r['status']=='found')} | "
              f"Partial: {sum(1 for r in results if r['status']=='partial')} | "
              f"No match: {sum(1 for r in results if r['status']=='no_match')} | "
              f"Needs manual: {sum(1 for r in results if r['status']=='needs_manual')}", flush=True)
    
    time.sleep(0.5)

# Final save
with open(PROGRESS_FILE, "w") as f:
    json.dump(progress, f, indent=2)

# Write CSV
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Store Number", "Store Name", "City", "State", "Phone", "Email",
                      "Owner/Principal", "Registered Agent", "Principal Address",
                      "Business Entity Name", "Source", "Status"])
    for r in sorted(results, key=lambda x: (x["state"], x["name"])):
        writer.writerow([r["store_number"], r["name"], r["city"], r["state"], 
                         r["phone"], r["email"], r["owner_name"], r["registered_agent"],
                         r["principal_address"], r["business_entity"], r["source"], r["status"]])

found = sum(1 for r in results if r["status"] == "found")
partial = sum(1 for r in results if r["status"] == "partial")
no_match = sum(1 for r in results if r["status"] == "no_match")
manual = sum(1 for r in results if r["status"] == "needs_manual")
print(f"\n=== DONE ===", flush=True)
print(f"Found: {found} | Partial: {partial} | No match: {no_match} | Needs manual: {manual}", flush=True)
print(f"CSV: {OUTPUT_CSV}", flush=True)
