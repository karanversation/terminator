"""
E*TRADE Benefits Parser.
Handles the "ByBenefitType_expanded.xlsx" export from E*TRADE.

Expected file location: source_files/etrade/

Parses ESPP and Restricted Stock (RSU) sheets. For each sheet it reads
the Totals row to get Sellable Qty and Est. Market Value (USD), then
converts to INR using ETRADE_USD_INR_RATE.

Holdings are classified as Stock (liquid US equities).
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

# USD → INR conversion rate. Update to match statement date.
ETRADE_USD_INR_RATE = 91.08

# Sheet name → benefit type label
_SHEET_LABEL = {
    "espp": "ESPP",
    "restricted stock": "RSU",
}


def _parse_sheet(df_raw: pd.DataFrame, label: str, report_date: date) -> Union[RawHolding, None]:
    """
    Parse a single E*TRADE benefit sheet (ESPP or RSU).
    df_raw: DataFrame read with header=None (row 0 = column headers).
    Uses positional indexing throughout to handle duplicate column names
    in complex RSU sheets.
    Returns a RawHolding or None if the sheet can't be parsed.
    """
    # Row 0 = headers (as list for positional lookup)
    headers = [str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[0]]
    data = df_raw.iloc[1:].reset_index(drop=True)

    # Find column positions by first occurrence of name
    def col_idx(keyword):
        for i, h in enumerate(headers):
            if keyword.lower() in h.lower():
                return i
        return None

    sellable_idx = col_idx("sellable qty")
    value_idx = col_idx("est. market value")
    if sellable_idx is None or value_idx is None:
        return None

    # Find symbol from first Purchase/Grant row (column 1)
    symbol = None
    for i in range(len(data)):
        rec = str(data.iat[i, 0]).strip()
        sym = str(data.iat[i, 1]).strip() if data.shape[1] > 1 else ""
        if rec in ("Purchase", "Grant") and sym and sym.lower() not in ("nan", ""):
            symbol = sym
            break

    if not symbol:
        return None

    # Find Totals row
    totals_row_idx = None
    for i in range(len(data)):
        if str(data.iat[i, 0]).strip() == "Totals":
            totals_row_idx = i
            break

    if totals_row_idx is None:
        return None

    try:
        sellable = float(str(data.iat[totals_row_idx, sellable_idx]).replace(",", ""))
        value_usd = float(str(data.iat[totals_row_idx, value_idx]).replace(",", ""))
    except (ValueError, IndexError):
        return None

    if sellable <= 0 or value_usd <= 0:
        return None

    price_usd = value_usd / sellable
    value_inr = round(value_usd * ETRADE_USD_INR_RATE, 2)
    price_inr = round(price_usd * ETRADE_USD_INR_RATE, 2)

    return RawHolding(
        report_date=report_date,
        asset_class="Stock",
        source="E*TRADE",
        name=f"{symbol} ({label})",
        isin=symbol,
        units=sellable,
        price=price_inr,
        value=value_inr,
        notes=f"USD ${value_usd:,.2f} @ ₹{ETRADE_USD_INR_RATE}/USD",
    )


class EtradeParser(BaseHoldingParser):
    source = "E*TRADE"
    asset_class = "Stock"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            suffix = filepath.suffix.lower()
            if suffix not in (".xlsx", ".xls"):
                return f"E*TRADE parser: expected xlsx/xls, got {filepath.name}"

            report_date = date.fromtimestamp(filepath.stat().st_mtime)

            xl = pd.ExcelFile(filepath)
            holdings: List[RawHolding] = []

            for sheet_name in xl.sheet_names:
                label = _SHEET_LABEL.get(sheet_name.lower().strip(), sheet_name)
                df_raw = xl.parse(sheet_name, header=None)
                holding = _parse_sheet(df_raw, label, report_date)
                if holding:
                    holdings.append(holding)

            if not holdings:
                return f"E*TRADE parser: no holdings found in {filepath.name}"

            return holdings

        except Exception as e:
            return f"E*TRADE parser error ({filepath.name}): {e}"
