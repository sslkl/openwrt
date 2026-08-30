#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = "https://api.estk.me/user/shop/products/2"
PAGE = "https://store.estk.me/products/2"
OUT = Path("estk-monitor/status.json")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_previous():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_result(result):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


previous = load_previous()
checked_at = now_iso()
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,900")
options.add_argument("--lang=en-US")

try:
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(40)
    driver.get(PAGE)
    payload = driver.execute_async_script(
        """
        const done = arguments[0];
        fetch('https://api.estk.me/user/shop/products/2', {
          method: 'GET',
          headers: {'Accept': '*/*', 'Content-Type': 'application/json'},
          mode: 'cors',
          credentials: 'omit',
          cache: 'no-store'
        }).then(async r => done({status:r.status, body:await r.text()}))
          .catch(e => done({status:0, body:'', error:String(e)}));
        """
    )
    status_code = int(payload.get("status", 0))
    if status_code != 200:
        raise RuntimeError(f"browser fetch HTTP {status_code}: {payload.get('error','')}")

    data = json.loads(payload["body"])
    product = (data.get("data") or {}).get("product") or data.get("product") or {}
    items = product.get("items") or []
    item = next((x for x in items if isinstance(x, dict) and x.get("title") == "ESTKme Red"), None)
    if item is None:
        raise RuntimeError("ESTKme Red not found in data.product.items")

    result = {
        "product": "ESTKme Red",
        "source": URL,
        "fetch_ok": True,
        "stock": item.get("stock"),
        "status": item.get("status"),
        "is_presale": item.get("is_presale"),
        "price": item.get("price"),
        "checked_at": checked_at,
        "note": "ok via Chromium"
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
        "note": f"browser fetch failed; retained last known values: {type(exc).__name__}: {exc}"
    }
finally:
    try:
        driver.quit()
    except Exception:
        pass

write_result(result)
