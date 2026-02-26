"""
Base classes for bank statement parsers.
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Union


@dataclass
class RawTransaction:
    date: date
    raw_description: str
    amount: float
    type: str           # 'Debit' | 'Credit'
    account: str        # e.g. "HDFC Diners Black CC"
    account_type: str   # 'credit_card' | 'savings'


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
