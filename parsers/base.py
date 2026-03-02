"""
Base classes for bank statement parsers and holding parsers.
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class RawTransaction:
    date: date
    raw_description: str
    amount: float
    type: str           # 'Debit' | 'Credit'
    account: str        # e.g. "HDFC Diners Black CC"
    account_type: str   # 'credit_card' | 'savings'
    source_file: str = ""  # filename of the source report (e.g. "hdfc_savings_apr25.txt")
    raw_line: str = ""    # literal original file row as a string


class BaseParser(ABC):
    """All parsers inherit from this class and set account/account_type as class attrs."""

    account: str
    account_type: str   # 'credit_card' | 'savings'

    @abstractmethod
    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        """
        Parse the file at filepath.
        Returns a list of RawTransaction on success, or an error string on failure.
        """
        ...

    def generate_id(self, txn: RawTransaction) -> str:
        """Deterministic SHA-256 id — same as db.make_txn_id()."""
        date_str = txn.date.strftime("%Y-%m-%d") if hasattr(txn.date, "strftime") else str(txn.date)
        key = f"{date_str}|{txn.raw_description}|{txn.amount:.4f}|{txn.account}"
        return hashlib.sha256(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Holding parsers — for networth tracker
# ---------------------------------------------------------------------------

@dataclass
class RawHolding:
    report_date: date
    asset_class: str        # 'Mutual Fund' | 'Stock' | 'Bond' | 'FD' | 'Bank'
    source: str             # 'CDSL CAS' | 'Zerodha' | 'MOFSL' | 'Stable Money' | account name
    name: str               # fund / stock / bond / bank name
    isin: Optional[str]     # ISIN / trading symbol where available
    units: Optional[float]  # units/shares (None for Bank, FD)
    price: Optional[float]  # NAV / LTP on report date (None for Bank, FD)
    value: float            # total INR value — the key field
    notes: Optional[str]    # maturity date, coupon rate, etc.


class BaseHoldingParser(ABC):
    """All holding parsers inherit from this class."""

    source: str         # human-readable source name
    asset_class: str    # default asset class for this parser

    @abstractmethod
    def parse(self, filepath: Path) -> "Union[List[RawHolding], str]":
        """
        Parse the file at filepath.
        Returns a list of RawHolding on success, or an error string on failure.
        """
        ...
