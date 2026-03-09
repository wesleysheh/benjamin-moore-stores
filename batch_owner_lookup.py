#!/usr/bin/env python3
"""Batch owner lookup - reads progress file, outputs stores needing lookup."""
import json

with open('mw_owner_progress.json') as f:
    data = json.load(f)

needs = [(k, v) for k, v in data.items() if v['status'] == 'needs_manual']
print(f"Total needing lookup: {len(needs)}")

# Group by state
by_state = {}
for k, v in needs:
    st = v['state']
    if st not in by_state:
        by_state[st] = []
    by_state[st].append((k, v))

for st in sorted(by_state, key=lambda s: len(by_state[s])):
    print(f"\n{st}: {len(by_state[st])} stores")
    for k, v in by_state[st]:
        print(f"  {v['name']} | {v['city']}, {st}")
