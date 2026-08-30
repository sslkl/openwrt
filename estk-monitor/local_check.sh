#!/bin/sh
set -eu

URL='https://api.estk.me/user/shop/products/2'
STATE_DIR="${STATE_DIR:-/tmp/estk-monitor}"
STATE_FILE="$STATE_DIR/status.json"
PREV_FILE="$STATE_DIR/previous.json"
mkdir -p "$STATE_DIR"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

NOW="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if ! curl --fail --silent --show-error --location \
  --connect-timeout 15 --max-time 30 \
  -H 'Accept: */*' \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://store.estk.me' \
  -H 'Referer: https://store.estk.me/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-site' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36' \
  "$URL" > "$TMP"; then
  printf '%s\n' "ESTK_FETCH_FAILED $NOW" >&2
  exit 2
fi

if command -v jq >/dev/null 2>&1; then
  ITEM="$(jq -c '((.data.product.items // .product.items // [])[]) | select(.title == "ESTKme Red")' "$TMP" | head -n 1)"
else
  echo 'jq is required' >&2
  exit 3
fi

[ -n "$ITEM" ] || { echo 'ESTKme Red not found' >&2; exit 4; }

jq -n \
  --arg product 'ESTKme Red' \
  --arg source "$URL" \
  --arg checked_at "$NOW" \
  --argjson item "$ITEM" \
  '{product:$product,source:$source,fetch_ok:true,stock:$item.stock,status:$item.status,is_presale:$item.is_presale,price:$item.price,checked_at:$checked_at}' \
  > "$STATE_FILE"

OLD_STOCK=''
if [ -s "$PREV_FILE" ] && jq -e . "$PREV_FILE" >/dev/null 2>&1; then
  OLD_STOCK="$(jq -r '.stock // empty' "$PREV_FILE")"
fi
NEW_STOCK="$(jq -r '.stock // empty' "$STATE_FILE")"

cp "$STATE_FILE" "$PREV_FILE"
cat "$STATE_FILE"

if [ -n "$NEW_STOCK" ] && [ "$NEW_STOCK" -gt 0 ] 2>/dev/null; then
  if [ -z "$OLD_STOCK" ] || [ "$OLD_STOCK" -eq 0 ] 2>/dev/null; then
    exit 10
  fi
fi

exit 0
