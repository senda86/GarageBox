#!/usr/bin/env python3
"""Aggiorna prices.json con i prezzi carburante di Istanbul (benzina, diesel, GPL).
Viene eseguito da GitHub Actions. Usa solo la libreria standard."""
import json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

URL = "https://api.opet.com.tr/api/fuelprices/prices?ProvinceCode=34"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Referer": "https://www.opet.com.tr/akaryakit-fiyatlari",
    "Origin": "https://www.opet.com.tr",
}
NAME_KEYS = ("productName", "ProductName", "fuelName", "name", "Name", "productShortName", "ProductShortName", "fuelType")
PRICE_KEYS = ("amount", "Amount", "price", "Price", "unitPrice", "value")
SKIP = ("v/max", "v-max", "vmax", "ecoforce", "97", "98", "100", "premium", "gazyağı", "gazyagi", "fuel oil", "fuel-oil", "kalorifer", "yüksek", "yuksek", "aygaz", "ısıtma")


def to_num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"\d+(?:[.,]\d+)?", v.replace(" ", ""))
        if m:
            return float(m.group(0).replace(",", "."))
    return None


def classify(name):
    n = name.lower()
    if any(k in n for k in SKIP):
        return None
    if "lpg" in n or "otogaz" in n:
        return "lpg"
    if "motorin" in n or "diesel" in n:
        return "motorin"
    if "kurşunsuz" in n or "kursunsuz" in n or "benzin" in n or "unleaded" in n or "gasoline" in n:
        return "benzin"
    return None


def walk(o, found):
    if isinstance(o, dict):
        name = next((o[k] for k in NAME_KEYS if isinstance(o.get(k), str)), None)
        price = next((to_num(o[k]) for k in PRICE_KEYS if k in o and to_num(o[k]) is not None), None)
        if name and price is not None:
            kind = classify(name)
            if kind:
                found.setdefault(kind, []).append(price)
        for v in o.values():
            walk(v, found)
    elif isinstance(o, list):
        for v in o:
            walk(v, found)


def parse(data):
    found = {}
    walk(data, found)
    # il prezzo standard è il più basso tra le varianti trovate
    return {k: round(min(v), 2) for k, v in found.items()}


def main():
    req = urllib.request.Request(URL, headers=HEADERS)
    try:
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        print("ERRORE di rete:", e)
        sys.exit(1)
    print("Risposta (primi 1500 caratteri):", raw[:1500])
    try:
        cur = parse(json.loads(raw))
    except Exception as e:
        print("ERRORE: la risposta non è JSON valido:", e)
        sys.exit(1)
    print("Prezzi trovati:", cur)
    if sorted(cur) != ["benzin", "lpg", "motorin"] or not all(5 < v < 1000 for v in cur.values()):
        print("ERRORE: prezzi mancanti o non plausibili, prices.json non modificato")
        sys.exit(1)
    try:
        old = json.load(open("prices.json", encoding="utf-8"))
    except Exception:
        old = {}
    today = datetime.now(timezone(timedelta(hours=3))).date().isoformat()
    prev = old.get("prev", {"d": today, **{k: None for k in cur}})
    if old.get("cur") and old["cur"] != cur:
        prev = {"d": old.get("asof", today), **old["cur"]}
    out = {
        "city": "Istanbul",
        "asof": today,
        "cur": cur,
        "prev": prev,
        "src": "https://www.opet.com.tr/akaryakit-fiyatlari",
    }
    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("prices.json aggiornato")


if __name__ == "__main__":
    main()
