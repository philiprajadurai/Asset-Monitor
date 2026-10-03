import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Return a connection to the Neon database."""
    return psycopg2.connect(os.environ["DATABASE_URL"])


def save_snapshot(total_value, breakdown):
    """Save today's portfolio snapshot. Updates if run twice on the same day."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO daily_snapshots (date, total_value, breakdown)
                VALUES (CURRENT_DATE, %s, %s)
                ON CONFLICT (date) DO UPDATE
                SET total_value = EXCLUDED.total_value,
                    breakdown = EXCLUDED.breakdown
            """, (total_value, psycopg2.extras.Json(breakdown)))
        conn.commit()
    finally:
        conn.close()


def get_yesterday_total():
    """Return the most recent prior-day total, or None if not available."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT total_value FROM daily_snapshots
                WHERE date < CURRENT_DATE
                ORDER BY date DESC LIMIT 1
            """)
            row = cur.fetchone()
            return float(row[0]) if row else None
    finally:
        conn.close()


def get_manual_assets():
    """Fetch all manually-entered assets (FD, gold, land)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM manual_assets ORDER BY id")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def add_manual_asset(asset):
    """Insert a new manual asset. `asset` is a dict with keys matching columns."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO manual_assets
                    (type, name, principal, rate, start_date,
                     quantity_grams, purity, area, location, guideline_value)
                VALUES
                    (%(type)s, %(name)s, %(principal)s, %(rate)s, %(start_date)s,
                     %(quantity_grams)s, %(purity)s, %(area)s, %(location)s,
                     %(guideline_value)s)
            """, {
                "type": asset["type"],
                "name": asset["name"],
                "principal": asset.get("principal"),
                "rate": asset.get("rate"),
                "start_date": asset.get("start_date"),
                "quantity_grams": asset.get("quantity_grams"),
                "purity": asset.get("purity"),
                "area": asset.get("area"),
                "location": asset.get("location"),
                "guideline_value": asset.get("guideline_value"),
            })
        conn.commit()
    finally:
        conn.close()


def get_us_stocks():
    """Fetch all US stock holdings."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM us_stocks ORDER BY id")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()