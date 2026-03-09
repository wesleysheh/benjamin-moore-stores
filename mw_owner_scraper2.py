import urllib.request
import json
import time
import ssl
import csv
import os
import re

PROGRESS_FILE = "/Users/clawbox-1/.openclaw/workspace/mw_owner_progress.json"
OUTPUT_CSV = "/Users/clawbox-1/.openclaw/workspace/mw_store_owners.csv"
ctx = ssl.create_default_context()

STATE_APIS = {
    "ID": {"search": "https://sosbiz.idaho.gov/api/Records/businesssearch",
           "detail": "https://sosbiz.idaho.gov/api/FilingDetail/business/{id}/false"},
    "ND": {"search": "https://firststop.sos.nd.gov/api/Records/businesssearch",
           "detail": "https://firststop.sos.nd.gov/api/FilingDetail/business/{id}/false"},
}

def do_search(api_url, search_value):
    payload = json.dumps({"SEARCH_VALUE": search_value, "STARTS_WITH_YN": "true", "ACTIVE_ONLY_YN": "true"}).encode('utf-8')
    req = urllib.request.Request(api_url, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read())

def do_detail(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        return json.loads(resp.read())

def clean_store_name(name):
    """Generate search variations from store name"""
    searches = []
    # Remove location suffix like "- MOSCOW" or "- COEUR"
    clean = re.sub(r'\s*-\s*[A-Z ]+$', '', name).strip()
    # Remove INC, LLC etc
    clean2 = re.sub(r',?\s*(INC|LLC|CO|CORP|COMPANY|LTD)\.?\s*$', '', clean, flags=re.I).strip()
    # Remove trailing punctuation
    clean2 = clean2.rstrip('.,')
    
    searches.append(clean)
    if clean2 != clean:
        searches.append(clean2)
    # Try first word only if multi-word and specific enough
    words = clean2.split()
    if len(words) >= 2 and len(words[0]) > 3:
        searches.append(words[0])
    
    return searches

def find_owner(state, store_name):
    if state not in STATE_APIS:
        return None
    
    api = STATE_APIS[state]
    searches = clean_store_name(store_name)
    
    for search_val in searches:
        if len(search_val) < 3:
            continue
        try:
            data = do_search(api["search"], search_val)
            rows = data.get("rows", {})
            if not rows:
                time.sleep(0.3)
                continue
            
            # Pick best match
            best = None
            store_words = set(store_name.upper().split())
            for rid, info in rows.items():
                title = info.get("TITLE", [""])[0].upper()
                # Score by word overlap
                title_words = set(re.sub(r'[^A-Z\s]', '', title).split())
                overlap = len(store_words & title_words)
                if best is None or overlap > best[1]:
                    best = (info, overlap)
            
            if best and best[0]:
                info = best[0]
                record_id = info.get("ID")
                result = {
                    "entity": info.get("TITLE", [""])[0],
                    "agent_search": info.get("AGENT", ""),
                    "owner": "",
                    "agent": "",
                    "principal_addr": "",
                }
                
                # Get detail
                if record_id:
                    try:
                        detail = do_detail(api["detail"].format(id=record_id))
                        for item in detail.get("DRAWER_DETAIL_LIST", []):
                            label = item.get("LABEL", "")
                            value = item.get("VALUE", "") or ""
                            if label == "Principal Address":
                                result["principal_addr"] = value.replace("\n", ", ")
                                result["owner"] = value.split("\n")[0] if value else ""
                            elif label == "Registered Agent":
                                lines = [l.strip() for l in value.split("\n") if l.strip()]
                                for line in lines:
                                    if line and not line.startswith("0") and line.lower() not in ("noncommercial", "commercial"):
                                        result["agent"] = line
                                        break
                        time.sleep(0.3)
                    except:
                        pass
                return result
        except Exception as e:
            time.sleep(1)
    return None

# Load stores
with open("/Users/clawbox-1/.openclaw/workspace/mw_stores.json") as f:
    stores = json.load(f)

# Load progress  
progress = {}
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE) as f:
        progress = json.load(f)

# Clear old bad results for ID and ND stores
for key in list(progress.keys()):
    r = progress[key]
    if r.get("state") in ("ID", "ND") and r.get("status") in ("no_match", "not_found"):
        del progress[key]

print(f"Loaded {len(stores)} stores, {len(progress)} already done", flush=True)

count = 0
for i, store in enumerate(stores):
    key = store["store_number"]
    if key in progress and progress[key].get("status") not in ("no_match", "not_found"):
        continue
    
    result = {
        "store_number": key, "name": store["name"], "city": store["city"],
        "state": store["state"], "phone": store["phone"], "email": store["email"],
        "owner_name": "", "registered_agent": "", "principal_address": "",
        "business_entity": "", "source": "", "status": "needs_manual"
    }
    
    if store["state"] in STATE_APIS:
        found = find_owner(store["state"], store["name"])
        if found:
            result["owner_name"] = found["owner"]
            result["registered_agent"] = found["agent"] or found["agent_search"]
            result["principal_address"] = found["principal_addr"]
            result["business_entity"] = found["entity"]
            result["source"] = f"{store['state']} SOS"
            result["status"] = "found" if found["owner"] else "partial"
        else:
            result["source"] = f"{store['state']} SOS"
            result["status"] = "no_match"
    
    progress[key] = result
    count += 1
    
    if count % 5 == 0:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)
        found_cnt = sum(1 for r in progress.values() if r.get("status") == "found")
        print(f"Progress: {i+1}/{len(stores)} | API found: {found_cnt} | Processed: {count}", flush=True)
    
    time.sleep(0.5)

# Final save
with open(PROGRESS_FILE, "w") as f:
    json.dump(progress, f, indent=2)

# Write CSV
all_results = list(progress.values())
with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Store Number", "Store Name", "City", "State", "Phone", "Email",
                      "Owner/Principal", "Registered Agent", "Principal Address",
                      "Business Entity Name", "Source", "Status"])
    for r in sorted(all_results, key=lambda x: (x["state"], x["name"])):
        writer.writerow([r["store_number"], r["name"], r["city"], r["state"],
                         r["phone"], r["email"], r["owner_name"], r["registered_agent"],
                         r["principal_address"], r["business_entity"], r["source"], r["status"]])

stats = {}
for r in all_results:
    s = r.get("status", "unknown")
    stats[s] = stats.get(s, 0) + 1
print(f"\n=== DONE ({len(all_results)} stores) ===", flush=True)
for s, c in sorted(stats.items()):
    print(f"  {s}: {c}", flush=True)
