#!/usr/bin/env python3
"""
Batch owner lookup using web search results.
Designed to be called from the agent with results processed by AI.
Outputs stores needing lookup as search queries.
"""
import json, sys

PROGRESS_FILE = 'mw_owner_progress.json'

def main():
    state = sys.argv[1] if len(sys.argv) > 1 else None
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    with open(PROGRESS_FILE) as f:
        data = json.load(f)
    
    needs = [(k, v) for k, v in data.items() 
             if isinstance(v, dict) 
             and v.get('status') in ('needs_manual', 'needs_parse')
             and (not state or v.get('state') == state)]
    
    print(f"Total needing lookup: {len(needs)}" + (f" in {state}" if state else ""))
    
    for i, (store_id, store) in enumerate(needs[:limit]):
        name = store['name']
        city = store['city']
        state = store['state']
        print(f"\n--- Store {store_id}: {name}, {city}, {state} ---")
        print(f"Search query: \"{name}\" {city} {state} owner LLC corporation")
        
if __name__ == '__main__':
    main()
