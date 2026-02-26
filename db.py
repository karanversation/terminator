"""
SQLite persistence layer for Terminator.
Handles schema init, upserts, manual overrides, and queries.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

DB_PATH = "terminator.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL,
    description     TEXT,
    raw_description TEXT,
    amount          REAL NOT NULL,
    type            TEXT NOT NULL,
    account         TEXT NOT NULL,
    account_type    TEXT NOT NULL,
    category        TEXT,
    category_source TEXT,
    payment_method  TEXT,
    month_year      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_date       ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_month_year ON transactions(month_year);
CREATE INDEX IF NOT EXISTS idx_category   ON transactions(category);
"""


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open (or create) the SQLite DB and apply schema migrations."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def make_txn_id(date: str, raw_description: str, amount: float, account: str) -> str:
    """Deterministic SHA-256 id for dedup."""
    key = f"{date}|{raw_description}|{amount:.4f}|{account}"
    return hashlib.sha256(key.encode()).hexdigest()


def upsert_transactions(conn: sqlite3.Connection, rows: List[Dict]) -> int:
    """
    INSERT OR IGNORE each row (dedup by id).
    Returns the number of new rows inserted.
    """
    if not rows:
        return 0
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR IGNORE INTO transactions
            (id, date, description, raw_description, amount, type,
             account, account_type, category, category_source,
             payment_method, month_year)
        VALUES
            (:id, :date, :description, :raw_description, :amount, :type,
             :account, :account_type, :category, :category_source,
             :payment_method, :month_year)
        """,
        rows,
    )
    inserted = cursor.rowcount
    conn.commit()
    return inserted


def update_category(
    conn: sqlite3.Connection,
    txn_id: str,
    category: str,
    source: str = "manual",
) -> None:
    """Persist a manual (or LLM) category correction."""
    conn.execute(
        "UPDATE transactions SET category = ?, category_source = ? WHERE id = ?",
        (category, source, txn_id),
    )
    conn.commit()


def update_type(
    conn: sqlite3.Connection,
    txn_id: str,
    txn_type: str,
    category: str,
    source: str = "rule",
) -> None:
    """Update the type and category of a transaction (used by transfer detection)."""
    conn.execute(
        "UPDATE transactions SET type = ?, category = ?, category_source = ? WHERE id = ?",
        (txn_type, category, source, txn_id),
    )
    conn.commit()


def load_transactions(
    conn: sqlite3.Connection, filters: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Load all transactions into a DataFrame.
    Optional filters dict: {column: value} applied as AND clauses.
    """
    query = "SELECT * FROM transactions"
    params: list = []
    if filters:
        clauses = [f"{col} = ?" for col in filters]
        query += " WHERE " + " AND ".join(clauses)
        params = list(filters.values())
    df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_uncategorized(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return rows with no category or category = 'Miscellaneous'."""
    df = pd.read_sql_query(
        """
        SELECT * FROM transactions
        WHERE category IS NULL OR category = 'Miscellaneous'
        """,
        conn,
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df
