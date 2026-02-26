"""
Transaction Loader
Orchestrates parsing of all transaction files and enrichment
"""

import os
from pathlib import Path

import pandas as pd

from config import DATA_DIR
from db import init_db, upsert_transactions, load_transactions, make_txn_id
from parsers import (
    parse_hdfc_cc_csv,
    parse_hdfc_savings_txt,
    parse_icici_csv,
    parse_icici_cc_csv,
    parse_sbi_csv,
    HdfcDinersParser,
    HdfcRegaliaParser,
    HdfcSavingsParser,
    IciciCCParser,
    IciciSavingsParser,
    SbiSavingsParser,
)
from .enricher import enrich_transactions
from .categorizer import categorize_transaction, identify_payment_method


def _pick_hdfc_cc_parser(filename: str):
    """Return the right HDFC CC parser based on the filename suffix."""
    if "2508" in filename:
        return HdfcDinersParser()
    else:
        return HdfcRegaliaParser()


# Folder → parser instance (or callable for dynamic dispatch)
_FOLDER_PARSER_MAP = {
    'hdfc_cc':       None,           # handled dynamically via _pick_hdfc_cc_parser
    'hdfc_savings':  HdfcSavingsParser(),
    'icici_cc':      IciciCCParser(),
    'icici_savings': IciciSavingsParser(),
    'sbi':           SbiSavingsParser(),
}

# Keep old function-based map for the legacy load path (used as fallback)
_LEGACY_PARSER_MAP = {
    'hdfc_cc':      parse_hdfc_cc_csv,
    'hdfc_savings': parse_hdfc_savings_txt,
    'icici_cc':     parse_icici_cc_csv,
    'icici_savings': parse_icici_csv,
    'sbi':          parse_sbi_csv,
}


def _raw_txns_to_db_rows(raw_txns, normalizer=None) -> list:
    """Convert RawTransaction objects into dicts suitable for upsert_transactions."""
    rows = []
    for txn in raw_txns:
        date_str = txn.date.strftime("%Y-%m-%d") if hasattr(txn.date, "strftime") else str(txn.date)
        month_year = date_str[:7]  # YYYY-MM

        # Normalize merchant name for the 'description' column
        if normalizer is not None:
            description = normalizer(txn.raw_description)
        else:
            description = txn.raw_description

        # Categorize: try normalized description first (cleaner merchant names),
        # fall back to raw description which has bank-specific patterns.
        category = categorize_transaction(description, txn.type)
        if category == 'Miscellaneous' and description != txn.raw_description:
            cat_raw = categorize_transaction(txn.raw_description, txn.type)
            if cat_raw != 'Miscellaneous':
                category = cat_raw

        # Payment method
        payment_method = identify_payment_method(
            txn.account, txn.raw_description, ""
        )

        txn_id = make_txn_id(date_str, txn.raw_description, txn.amount, txn.account)

        rows.append({
            "id": txn_id,
            "date": date_str,
            "description": description,
            "raw_description": txn.raw_description,
            "amount": txn.amount,
            "type": txn.type,
            "account": txn.account,
            "account_type": txn.account_type,
            "category": category,
            "category_source": "rule",
            "payment_method": payment_method,
            "month_year": month_year,
        })
    return rows


def load_all_transactions():
    """
    Load and parse all transaction files from the data directory.
    Writes new rows to SQLite DB (dedup by sha256 id).
    Returns (transactions_df, error_files_list) — same API as before.
    """
    try:
        from processors.normalizer import normalize
    except ImportError:
        normalize = None

    conn = init_db()
    error_files = []

    for folder_name in sorted(os.listdir(DATA_DIR)):
        folder_path = os.path.join(DATA_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        if folder_name not in _FOLDER_PARSER_MAP and folder_name not in _LEGACY_PARSER_MAP:
            continue

        for file in sorted(os.listdir(folder_path)):
            file_lower = file.lower()
            if not (file_lower.endswith('.csv') or file_lower.endswith('.txt')):
                continue

            filepath = Path(folder_path) / file

            # Pick parser: use new class-based parser when available
            if folder_name == 'hdfc_cc':
                parser = _pick_hdfc_cc_parser(file)
            else:
                parser = _FOLDER_PARSER_MAP.get(folder_name)

            if parser is None:
                continue

            result = parser.parse(filepath)

            if isinstance(result, str):
                error_files.append(result)
                continue

            if result:
                db_rows = _raw_txns_to_db_rows(result, normalizer=normalize)
                upsert_transactions(conn, db_rows)

    # Re-run rule-based categorization on existing rows whose description may have
    # changed (e.g. normalizer was updated) or whose category is still Miscellaneous.
    # This does NOT touch rows with category_source = 'manual' or 'llm'.
    _recategorize_rule_based(conn, normalize)

    # Re-run payment method identification on all rows (fixes stale 'Other' values)
    _fix_payment_methods(conn)

    # Run CC payment dedup / transfer detection using account_type
    _mark_cc_payments_as_transfer(conn)

    # Load from DB and convert to the legacy DataFrame format
    df = load_transactions(conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(), error_files

    df = _db_df_to_legacy(df)
    df = df.sort_values('Date', ascending=False)
    return df, error_files


def _recategorize_rule_based(conn, normalizer=None):
    """
    Re-run categorization on all rows with category_source='rule'.
    Also re-normalizes the description column so stale/pre-fix descriptions get updated.
    Preserves manual and llm overrides.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT id, raw_description, type FROM transactions WHERE category_source = 'rule'"
    )
    rows = cur.fetchall()
    if not rows:
        return

    updates = []
    for row in rows:
        txn_id, raw_desc, txn_type = row

        # Re-normalize
        if normalizer is not None:
            description = normalizer(raw_desc)
        else:
            description = raw_desc

        # Categorize: normalized first, then raw fallback
        category = categorize_transaction(description, txn_type)
        if category == 'Miscellaneous' and description != raw_desc:
            cat_raw = categorize_transaction(raw_desc, txn_type)
            if cat_raw != 'Miscellaneous':
                category = cat_raw

        updates.append((description, category, txn_id))

    conn.executemany(
        "UPDATE transactions SET description = ?, category = ? WHERE id = ?",
        updates,
    )
    conn.commit()


def _fix_payment_methods(conn):
    """
    Re-run payment method identification on all rows.
    Fixes stale 'Other' values caused by the old code passing file_name="" always.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, raw_description, account FROM transactions")
    rows = cur.fetchall()
    if not rows:
        return
    updates = []
    for txn_id, raw_desc, account in rows:
        pm = identify_payment_method(account, raw_desc, "")
        updates.append((pm, txn_id))
    conn.executemany(
        "UPDATE transactions SET payment_method = ? WHERE id = ?", updates
    )
    conn.commit()


def _mark_cc_payments_as_transfer(conn):
    """
    Reclassify credit card bill payments from savings accounts as 'Transfer'.
    Uses account_type == 'savings' so any future savings account works automatically.
    """
    conn.execute(
        """
        UPDATE transactions
        SET type = 'Transfer'
        WHERE category = 'Credit Card Payment'
          AND account_type = 'savings'
          AND type = 'Debit'
        """
    )
    conn.commit()


def _db_df_to_legacy(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the DB schema DataFrame into the column format the UI expects."""
    out = pd.DataFrame()
    out['Date'] = df['date']
    out['Description'] = df['description'].fillna(df['raw_description'])
    out['Amount'] = df['amount']
    out['Type'] = df['type']
    out['Category'] = df['category'].fillna('Miscellaneous')
    out['Payment Method'] = df['payment_method'].fillna('Other')
    out['Source'] = df['account']
    out['Month-Year'] = df['month_year']
    out['account_type'] = df['account_type']
    out['id'] = df['id']
    out['raw_description'] = df['raw_description']
    out['category_source'] = df['category_source']

    # Ensure Date is datetime
    out['Date'] = pd.to_datetime(out['Date'])

    return out
