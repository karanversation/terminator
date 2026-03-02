"""
Networth Loader — orchestrates all holding parsers and bank balance extraction.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from db import init_db
from networth.db import init_networth_db, load_holdings, to_db_rows, upsert_holdings, make_holding_id
from parsers.cams import CamsParser
from parsers.carta import CartaParser
from parsers.etrade import EtradeParser
from parsers.liability import LiabilityParser
from parsers.property import PropertyParser
from parsers.vehicle import VehicleParser
from parsers.hdfc import HdfcSavingsParser
from parsers.icici import IciciSavingsParser
from parsers.indmoney import IndmoneyParser
from parsers.mofsl import MofslParser
from parsers.sbi import SbiSavingsParser
from parsers.stablemoney import StableMoneyParser
from parsers.zerodha import ZerodhaParser
from parsers.base import RawHolding

DATA_DIR = Path("source_files")

_HOLDING_FOLDER_MAP = {
    "cams": CamsParser(),
    "carta": CartaParser(),
    "etrade": EtradeParser(),
    "liabilities": LiabilityParser(),
    "property": PropertyParser(),
    "vehicles": VehicleParser(),
    "zerodha": ZerodhaParser(),
    "motilal": MofslParser(),
    "indmoney": IndmoneyParser(),
    "stablemoney": StableMoneyParser(),
}

_SAVINGS_PARSERS = [
    (HdfcSavingsParser(), "hdfc_savings"),
    (IciciSavingsParser(), "icici_savings"),
    (SbiSavingsParser(), "sbi"),
]

_SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".pdf"}


def _make_bank_holding(account: str, report_date, balance: float) -> dict:
    """Build a DB-ready dict for a bank balance row."""
    date_str = (
        report_date.strftime("%Y-%m-%d")
        if hasattr(report_date, "strftime")
        else str(report_date)
    )
    return {
        "id": make_holding_id(date_str, account, account, "Bank"),
        "report_date": date_str,
        "asset_class": "Bank",
        "source": account,
        "name": account,
        "isin": None,
        "units": None,
        "price": None,
        "value": balance,
        "notes": None,
    }


def load_all_holdings() -> Tuple[pd.DataFrame, List[str]]:
    """
    Parse all holding files and bank statements, upsert into DB, return DataFrame + errors.
    """
    conn = init_db()
    init_networth_db(conn)
    errors: List[str] = []

    # 1. Parse holding report files from subfolders
    for folder, parser in _HOLDING_FOLDER_MAP.items():
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            continue
        for file in sorted(folder_path.iterdir()):
            if file.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            result = parser.parse(file)
            if isinstance(result, str):
                errors.append(result)
            else:
                rows = to_db_rows(result)
                upsert_holdings(conn, rows)

    # 2. Bank closing balances from existing savings statement files
    for parser, folder in _SAVINGS_PARSERS:
        folder_path = DATA_DIR / folder
        if not folder_path.exists():
            continue
        for file in sorted(folder_path.iterdir()):
            if file.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            try:
                report_date, balance = parser.get_closing_balance(file)
                row = _make_bank_holding(parser.account, report_date, balance)
                upsert_holdings(conn, [row])
            except Exception as e:
                errors.append(str(e))

    df = load_holdings(conn)
    return df, errors


def get_source_status() -> List[dict]:
    """
    Return a list of dicts describing each source folder:
    {source, folder, file_count, exists}
    """
    status = []

    for folder, parser in _HOLDING_FOLDER_MAP.items():
        folder_path = DATA_DIR / folder
        files = (
            [f for f in folder_path.iterdir() if f.suffix.lower() in _SUPPORTED_EXTENSIONS]
            if folder_path.exists()
            else []
        )
        status.append({
            "source": parser.source,
            "folder": str(folder_path),
            "file_count": len(files),
            "exists": folder_path.exists(),
        })

    for parser, folder in _SAVINGS_PARSERS:
        folder_path = DATA_DIR / folder
        files = (
            [f for f in folder_path.iterdir() if f.suffix.lower() in _SUPPORTED_EXTENSIONS]
            if folder_path.exists()
            else []
        )
        status.append({
            "source": parser.account + " (Bank Balance)",
            "folder": str(folder_path),
            "file_count": len(files),
            "exists": folder_path.exists(),
        })

    return status
