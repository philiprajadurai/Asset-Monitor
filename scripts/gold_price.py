"""
Fetches today's gold prices from Kalyan Jewellers Chennai page.

The page is a Next.js app: it embeds all rates as JSON inside a
<script id="__NEXT_DATA__"> tag. We extract that JSON directly,
which is far more reliable than parsing HTML tables.
"""
import json
import re
import requests
from bs4 import BeautifulSoup

KALYAN_URL = "https://store.kalyanjewellers.net/gold-rate/chennai/en"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _extract_next_data(html):
    """Pull the __NEXT_DATA__ JSON object out of the page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    return json.loads(tag.string)


def _parse_karat_label(entry):
    """
    Each entry in goldRate looks like:
      {"karat_24(995)": {...}}  or  {"karat_22": {...}}
    Return '24K', '22K', etc. based on the key.
    """
    for key in entry.keys():
        m = re.match(r"karat_(\d+)", key)
        if m:
            return f"{m.group(1)}K"
    return None


def fetch_gold_prices():
    """
    Return a dict like {'24K': 14918, '22K': 13675, '18K': 11189, '14K': 8702}
    (price per gram, in INR). Returns {} if scraping fails.
    """
    try:
        resp = requests.get(KALYAN_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[warn] Could not fetch gold prices: {e}")
        return {}

    data = _extract_next_data(resp.text)
    if not data:
        print("[warn] Could not find __NEXT_DATA__ in page.")
        return {}

    try:
        gold_rate_list = data["props"]["pageProps"]["goldRate"]
    except (KeyError, TypeError):
        print("[warn] goldRate not found in page data.")
        return {}

    prices = {}
    for entry in gold_rate_list:
        label = _parse_karat_label(entry)
        if not label:
            continue
        # Extract the inner dict (the value of the karat_NN key)
        inner = list(entry.values())[0]
        price = inner.get("price_per_gram")
        if price and label not in prices:
            # Keep the first occurrence — for 24K, page has both
            # karat_24(995) and karat_24(999); both show the same price.
            prices[label] = int(price)

    if not prices:
        print("[warn] Could not parse gold prices from page data.")

    return prices


def get_price_for_purity(purity, prices=None):
    """
    Return price per gram for a given purity string.
    Falls back to 22K if purity is unknown.
    """
    if prices is None:
        prices = fetch_gold_prices()

    if not prices:
        return 0.0

    key = (purity or "22K").upper().replace(" ", "")
    if key in prices:
        return float(prices[key])

    # Common variants
    variants = {
        "24": "24K", "24KT": "24K", "24KARAT": "24K",
        "22": "22K", "22KT": "22K", "22KARAT": "22K",
        "18": "18K", "18KT": "18K", "18KARAT": "18K",
        "14": "14K", "14KT": "14K", "14KARAT": "14K",
    }
    if key in variants:
        return float(prices.get(variants[key], 0))

    # Fallback to 22K (most common jewellery purity)
    return float(prices.get("22K", 0))