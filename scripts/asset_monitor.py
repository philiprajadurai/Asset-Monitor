"""
Asset Monitor
-------------
Computes total portfolio value across:
- Stock holdings from Upstox (Indian shares + mutual funds)
- US stocks (Upstox + INDmoney) via Yahoo Finance
- Fixed deposits (accrued interest)
- Gold (live price from Kalyan Jewellers, per purity)
- Land (guideline value, updated manually)

Saves a daily snapshot and prints the day-over-day change.
"""
import os
from datetime import datetime, date
import httpx
from dotenv import load_dotenv

from db import (
    save_snapshot,
    get_yesterday_total,
    get_manual_assets,
    get_us_stocks,
)
from gold_price import fetch_gold_prices, get_price_for_purity
from us_stocks import calculate_us_stock_value

load_dotenv()

UPSTOX_TOKEN = os.environ.get("UPSTOX_ACCESS_TOKEN", "")


# ---------- Indian stocks via Upstox ----------

def fetch_upstox_holdings():
    """Fetch long-term Indian holdings from Upstox."""
    if not UPSTOX_TOKEN:
        print("[warn] UPSTOX_ACCESS_TOKEN not set; skipping Indian stocks.")
        return []

    url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
    headers = {
        "Authorization": f"Bearer {UPSTOX_TOKEN}",
        "Accept": "application/json",
    }
    resp = httpx.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"[warn] Upstox API error {resp.status_code}: {resp.text[:200]}")
        return []
    return resp.json().get("data", [])


def calculate_stock_value(holdings):
    """Sum last_price × quantity for each holding."""
    total = 0.0
    for h in holdings:
        qty = float(h.get("quantity", 0))
        price = float(h.get("last_price", 0))
        total += qty * price
    return total


# ---------- FD value ----------

def calculate_fd_value(principal, rate, start_date):
    """Simple daily compounding FD value."""
    if isinstance(start_date, str):
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start = start_date
    days = (date.today() - start).days
    return float(principal) * (1 + float(rate) / 36500) ** days


# ---------- Main aggregation ----------

def compute_portfolio():
    """Return (total_value, breakdown_dict)."""
    manual = get_manual_assets()
    us = get_us_stocks()

    # Indian stocks (Upstox)
    holdings = fetch_upstox_holdings()
    stock_value = calculate_stock_value(holdings)

    # FDs
    fd_value = 0.0
    for a in manual:
        if a["type"] == "fd":
            fd_value += calculate_fd_value(a["principal"], a["rate"], a["start_date"])

    # Gold
    gold_prices = fetch_gold_prices()
    if gold_prices:
        print(f"[info] Gold prices per gram: {gold_prices}")

    gold_value = 0.0
    for a in manual:
        if a["type"] == "gold":
            qty = float(a["quantity_grams"] or 0)
            purity = a.get("purity") or "22K"
            price_per_gram = get_price_for_purity(purity, gold_prices)
            gold_value += qty * price_per_gram

    # Land
    land_value = 0.0
    for a in manual:
        if a["type"] == "land":
            land_value += float(a["guideline_value"] or 0)

    # US stocks
    us_value, us_details = calculate_us_stock_value(us)

    breakdown = {
        "stocks_in": round(stock_value, 2),
        "stocks_us": round(us_value, 2),
        "fd": round(fd_value, 2),
        "gold": round(gold_value, 2),
        "land": round(land_value, 2),
    }
    total = sum(breakdown.values())
    return round(total, 2), breakdown


def main():
    print(f"--- Asset Monitor: {date.today().isoformat()} ---")

    total, breakdown = compute_portfolio()

    print(f"\nToday's total: ₹{total:,.2f}")
    for k, v in breakdown.items():
        print(f"  {k:10s}: ₹{v:,.2f}")

    yesterday = get_yesterday_total()
    if yesterday and yesterday > 0:
        change = total - yesterday
        pct = (change / yesterday) * 100
        arrow = "▲" if change >= 0 else "▼"
        print(f"\n{arrow} Change from last snapshot: ₹{change:,.2f} ({pct:+.2f}%)")
    else:
        print("\n(No previous snapshot yet — this is the first run.)")

    save_snapshot(total, breakdown)
    print("\nSnapshot saved to Neon.")


if __name__ == "__main__":
    main()