#!/bin/bash
# Fetch all BM stores, paginating through results
OUTPUT="/Users/clawbox-1/.openclaw/workspace/bm_all_stores.json"
API="https://api.benjaminmoore.io/retailer/stores"
KEY="48c3c3e75b424f97904f9659da65b4d0"

echo "[" > "$OUTPUT"
OFFSET=0
LIMIT=500
FIRST=1

while true; do
  echo "Fetching offset=$OFFSET..." >&2
  RESP=$(curl -s "${API}?version=v1.0&latitude=39.7392&longitude=-104.9903&radius=5000&limit=${LIMIT}&offset=${OFFSET}&locale=en-us&countryCode=US" \
    -H "Ocp-Apim-Subscription-Key: ${KEY}" \
    -H "Accept: application/json")
  
  IS_LAST=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('is_last',True))")
  TOTAL=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total',0))")
  COUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('stores',[])))")
  
  echo "  total=$TOTAL, got=$COUNT, is_last=$IS_LAST" >&2
  
  # Extract stores and append
  if [ "$FIRST" = "1" ]; then
    echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(json.dumps(s)+',' if i<len(d['stores'])-1 else json.dumps(s)) for i,s in enumerate(d.get('stores',[]))]" >> "$OUTPUT"
    FIRST=0
  else
    echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(','+json.dumps(s)) for s in d.get('stores',[])]" >> "$OUTPUT"
  fi
  
  if [ "$IS_LAST" = "True" ] || [ "$COUNT" = "0" ]; then
    break
  fi
  
  OFFSET=$((OFFSET + LIMIT))
done

echo "]" >> "$OUTPUT"
echo "Done. Saved to $OUTPUT" >&2
