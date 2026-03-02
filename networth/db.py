"""
SQLite persistence layer for the Networth Tracker.
Shares terminator.db with the transaction tracker.
"""

import hashlib
import sqlite3
from datetime import date
from typing import Dict, List, Optional

import pandas as pd

_SCHEMA = """
CREATE TABLE IF NOT EXISTS asset_holdings (
    id           TEXT PRIMARY KEY,
    report_date  TEXT NOT NULL,
    asset_class  TEXT NOT NULL,
    source       TEXT NOT NULL,
    name         TEXT NOT NULL,
    isin         TEXT,
    units        REAL,
    price        REAL,
    value        REAL NOT NULL,
    notes        TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ah_date  ON asset_holdings(report_date);
CREATE INDEX IF NOT EXISTS idx_ah_class ON asset_holdings(asset_class);
"""


def init_networth_db(conn: sqlite3.Connection) -> None:
    """Create asset_holdings table if it doesn't exist. Call after init_db()."""
    conn.executescript(_SCHEMA)
    conn.commit()


def make_holding_id(report_date: str, source: str, name: str, asset_class: str) -> str:
    """Deterministic SHA-256 id for dedup."""
    key = f"{report_date}|{source}|{name}|{asset_class}"
    return hashlib.sha256(key.encode()).hexdigest()


def upsert_holdings(conn: sqlite3.Connection, rows: List[Dict]) -> int:
    """
    INSERT OR REPLACE each row (re-import updates values for same date/source/name).
    Also removes stale rows for the same source+name+report_date with a different
    asset_class (handles cases where a holding's class changes across re-imports).
    Returns number of rows processed.
    """
    if not rows:
        return 0
    cursor = conn.cursor()
    for row in rows:
        # Remove any stale row with a different asset_class for the same holding
        cursor.execute(
            """
            DELETE FROM asset_holdings
            WHERE source = ? AND name = ? AND report_date = ? AND asset_class != ?
            """,
            (row["source"], row["name"], row["report_date"], row["asset_class"]),
        )
    cursor.executemany(
        """
        INSERT OR REPLACE INTO asset_holdings
            (id, report_date, asset_class, source, name, isin, units, price, value, notes)
        VALUES
            (:id, :report_date, :asset_class, :source, :name, :isin, :units, :price, :value, :notes)
        """,
        rows,
    )
    count = cursor.rowcount
    conn.commit()
    return count


def load_holdings(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all asset holdings into a DataFrame."""
    df = pd.read_sql_query(
        "SELECT * FROM asset_holdings ORDER BY report_date DESC, value DESC",
        conn,
    )
    if not df.empty:
        df["report_date"] = pd.to_datetime(df["report_date"])
    return df


def to_db_rows(holdings: list) -> List[Dict]:
    """Convert a list of RawHolding objects to dicts ready for upsert_holdings."""
    rows = []
    for h in holdings:
        date_str = (
            h.report_date.strftime("%Y-%m-%d")
            if hasattr(h.report_date, "strftime")
            else str(h.report_date)
        )
        rows.append({
            "id": make_holding_id(date_str, h.source, h.name, h.asset_class),
            "report_date": date_str,
            "asset_class": h.asset_class,
            "source": h.source,
            "name": h.name,
            "isin": h.isin,
            "units": h.units,
            "price": h.price,
            "value": h.value,
            "notes": h.notes,
        })
    return rows
