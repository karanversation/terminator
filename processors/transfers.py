"""
Internal transfer detection.
Finds debit/credit pairs between savings accounts that represent the same
money moving from one account to another, and marks both sides as Transfer.
"""

import sqlite3


def detect_internal_transfers(conn: sqlite3.Connection) -> int:
    """
    Find debit in savings account A that matches a credit in any savings account B:
    - Same amount ±₹1
    - Within 5 calendar days of each other
    - Both must have account_type = 'savings' (CC debits are real expenses)
    - Marks both rows: type='Transfer', category='Internal Transfer', category_source='rule'

    Returns the number of debit/credit pairs found (each pair counts as 1).
    """
    # Fetch all savings debits that aren't already Transfer
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, date, amount, account
        FROM transactions
        WHERE account_type = 'savings'
          AND type = 'Debit'
          AND category != 'Internal Transfer'
        ORDER BY date
        """
    )
    debits = cur.fetchall()

    # Fetch all savings credits
    cur.execute(
        """
        SELECT id, date, amount, account
        FROM transactions
        WHERE account_type = 'savings'
          AND type = 'Credit'
          AND category != 'Internal Transfer'
        ORDER BY date
        """
    )
    credits = cur.fetchall()

    from datetime import datetime, timedelta

    def parse_date(d):
        if isinstance(d, str):
            return datetime.strptime(d[:10], "%Y-%m-%d")
        return d

    matched_debit_ids = set()
    matched_credit_ids = set()
    pairs = 0

    for debit in debits:
        d_id, d_date, d_amount, d_account = debit
        d_dt = parse_date(d_date)

        for credit in credits:
            c_id, c_date, c_amount, c_account = credit

            # Skip already matched
            if c_id in matched_credit_ids:
                continue

            c_dt = parse_date(c_date)

            # Must be different accounts (can't be same account)
            if d_account == c_account:
                continue

            # Amount must match within ₹1
            if abs(d_amount - c_amount) > 1.0:
                continue

            # Date must be within 5 calendar days
            if abs((d_dt - c_dt).days) > 5:
                continue

            # Match found
            matched_debit_ids.add(d_id)
            matched_credit_ids.add(c_id)
            pairs += 1
            break  # Each debit matches at most one credit

    # Update matched rows in DB
    if matched_debit_ids:
        for txn_id in matched_debit_ids:
            conn.execute(
                """
                UPDATE transactions
                SET type = 'Transfer', category = 'Internal Transfer', category_source = 'rule'
                WHERE id = ?
                """,
                (txn_id,),
            )
        for txn_id in matched_credit_ids:
            conn.execute(
                """
                UPDATE transactions
                SET type = 'Transfer', category = 'Internal Transfer', category_source = 'rule'
                WHERE id = ?
                """,
                (txn_id,),
            )
        conn.commit()

    return pairs
