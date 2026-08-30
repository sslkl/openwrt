#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://api.estk.me/user/shop/products/2"
JINA = "https://r.jina.ai/https://api.estk.me/user/shop/products/2"
OUT = Path("estk-monitor/status.json")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_previous():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_item(data):
    product = (data.get("data") or {}).get("product") or data.get("product") or {}
    items = product.get("items") or []
    item = next((x for x in items if isinstance(x, dict) and x.get("title") == "ESTKme Red"), None)
    if item is None:
        raise RuntimeError("ESTKme Red not found in data.product.items")
    return item


def fetch_item():
    req = urllib.request.Request(
        JINA,
        headers={
            "User-Agent": "Mozilla/5.0 ESTK-stock-monitor/1.0",
            "X-No-Cache": "true",
            "X-Engine": "browser",
            "X-Respond-With": "text",
            "DNT": "1",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        text = response.read().decode("utf-8", errors="replace").strip()

    candidates = [text]
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first:last + 1])

    errors = []
    for candidate in candidates:
        try:
            return parse_item(json.loads(candidate))
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("Jina response did not contain parseable ESTK JSON: " + " | ".join(errors))


def write_result(result):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


previous = load_previous()
checked_at = now_iso()

try:
    item = fetch_item()
    result = {
        "product": "ESTKme Red",
        "source": URL,
        "fetch_ok": True,
        "stock": item.get("stock"),
        "status": item.get("status"),
        "is_presale": item.get("is_presale"),
        "price": item.get("price"),
        "checked_at": checked_at,
        "note": "ok via Jina browser relay"
    }
except Exception as exc:
    result = {
        "product": "ESTKme Red",
        "source": URL,
        "fetch_ok": False,
        "stock": previous.get("stock"),
        "status": previous.get("status"),
        "is_presale": previous.get("is_presale"),
        "price": previous.get("price"),
        "checked_at": checked_at,
        "note": f"Jina fetch failed; retained last known values: {type(exc).__name__}: {exc}"
    }

write_result(result)
