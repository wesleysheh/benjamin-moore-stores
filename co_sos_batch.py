#!/usr/bin/env python3
"""Batch CO SOS search results - processes a list of search terms and extracts entity details."""

import json
import sys

# List of CO stores to search: (store_ids, search_term)
CO_SEARCHES = [
    (["10015794", "10019265", "10023289"], "moore lumber"),
    (["10014015", "10014276", "10014573"], "co-op country"),
    (["10014028", "10015785"], "big tool box"),
    (["10014055", "10014056"], "quality farm"),
    (["10000195"], "mjk sales"),
    (["10000481"], "colors inc"),
    (["10000981"], "denver tru-value"),
    (["10001064"], "ponderosa paint"),
    (["10001224"], "wylie"),
    (["10002722"], "park supply"),
    (["10002922"], "home store lamar"),
    (["10003533"], "wray lumber"),
    (["10003839"], "poncha lumber"),
    (["10004023"], "mountain high paint"),
    (["10004865"], "manweiler"),
    (["10006322"], "collbran supply"),
    (["10006789"], "mountain color"),
    (["10006839"], "northside paint"),
    (["10006980"], "arkansas valley lumber"),
    (["10009824"], "noco paint"),
    (["10010512"], "g4 coatings"),
    (["10011128"], "juniper paints"),
    (["10012449"], "ajax supply"),
    (["10012697"], "arvada flooring"),
    (["10013065"], "herman lumber"),
    (["10013129"], "la junta trading"),
    (["10013163"], "pandhandle creek"),
    (["10013336"], "stratton equity"),
    (["10013825"], "pronghorn country"),
    (["10014576"], "choice building supply"),
    (["10014582"], "delta hardware"),
    (["10014594"], "mcguckin"),
    (["10014639"], "valley hardware meeker"),
    (["10015646"], "steve paint supply"),
    (["10016432"], "agfinity"),
    (["10016433"], "poudre valley"),
    (["10017578"], "aguilar mercantile"),
    (["10018256"], "m m decorating"),
    (["10019644"], "colored red"),
    (["10021008"], "budget home supply"),
    (["10021558"], "paint pallet"),
    (["10021993"], "lamar bms"),
    (["10013238"], "rocky mountain rebar"),
]

# Results found so far (from browser lookups)
FOUND = {
    "moore lumber": {
        "owner_name": "Folkestad Fazekas Barrick Patoile & James, P.C. (Registered Agent/Law Firm)",
        "registered_agent": "Folkestad Fazekas Barrick Patoile & James, P.C.",
        "principal_address": "186 Mt. Evans Boulevard, Pine, CO 80470",
        "business_entity": "Moore Lumber & Hardware, Inc. (CO Corp, ID 20031381982)",
        "source": "CO Secretary of State",
    },
}

if __name__ == "__main__":
    print(json.dumps(CO_SEARCHES, indent=2))
