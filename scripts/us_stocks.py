"""
Fetches live prices for US stocks via Yahoo Finance's public quote API.

No API key needed. Yahoo Finance returns price in USD; we also fetch
the USD -> INR exchange rate so the value can be shown in rupees.
"""
import requests

# Yahoo Finance uses these suffixes for currency pairs:
#   USDINR=X  -> US Dollar to Indian Rupee
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_FX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_price_usd(ticker):
    """
    Return the latest price in USD for a ticker (e.g. 'AAPL'), or None.
    """
    url = YAHOO_QUOTE_URL.format(ticker=ticker.upper())
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[warn] Could not fetch price for {ticker}: {e}")
        return None

    try:
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        return float(price)
    except (KeyError, TypeError, IndexError):
        print(f"[warn] Could not parse price for {ticker}.")
        return None


def fetch_usd_to_inr():
    """
    Return the current USD -> INR exchange rate, or None.
    """
    try:
        resp = requests.get(YAHOO_FX_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        rate = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return float(rate)
    except Exception as e:
        print(f"[warn] Could not fetch USD/INR rate: {e}")
        return None


def calculate_us_stock_value(holdings):
    """
    Given a list of dicts like [{'ticker': 'AAPL', 'quantity': 10}, ...],
    return (total_value_inr, details_dict).
    """
    if not holdings:
        return 0.0, {}

    fx = fetch_usd_to_inr()
    if fx is None:
        print("[warn] Skipping US stocks — no FX rate available.")
        return 0.0, {}

    print(f"[info] USD/INR rate: {fx:.2f}")

    total = 0.0
    details = {}

    for h in holdings:
        ticker = h["ticker"].upper()
        qty = float(h["quantity"])
        price_usd = fetch_price_usd(ticker)
        if price_usd is None:
            continue
        value_inr = qty * price_usd * fx
        total += value_inr
        details[ticker] = {
            "quantity": qty,
            "price_usd": round(price_usd, 2),
            "value_inr": round(value_inr, 2),
            "broker": h.get("broker") or "",
        }
        print(f"[info] {ticker}: {qty} × ${price_usd:.2f} × ₹{fx:.2f} = ₹{value_inr:,.2f}")

    return round(total, 2), details