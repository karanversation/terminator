"""
Zerodha Holdings Parser.
Handles two formats:
  1. Equity Holdings Statement XLSX (from Console → Reports → Holdings)
     Rows: Symbol, ISIN, Sector, Quantity Available, ..., Previous Closing Price, ...
     Date extracted from "Equity Holdings Statement as on YYYY-MM-DD" row.
  2. Simple Holdings CSV (from Console → Portfolio → Holdings → Download)
     Columns: Instrument, Qty., Avg. cost, LTP, Cur. val, ...

Expected file location: source_files/zerodha/
Report date: parsed from file content (format 1) or filename/mtime (format 2).
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

# Aliases for simple CSV format
_NAME_ALIASES = ["instrument", "symbol", "stock", "scrip", "name"]
_UNITS_ALIASES = ["qty.", "qty", "quantity available", "quantity", "shares"]
_PRICE_ALIASES = ["ltp", "previous closing price", "cmp", "market price", "current price", "close price"]
_VALUE_ALIASES = ["cur. val", "cur.val", "current value", "market value", "value"]


def _find_col(columns, aliases):
    lower_cols = {col.lower().strip(): col for col in columns}
    for alias in aliases:
        if alias in lower_cols:
            return lower_cols[alias]
    for alias in aliases:
        for col_lower, col in lower_cols.items():
            if alias in col_lower:
                return col
    return None


def _parse_report_date_from_filename(filepath: Path) -> date:
    m = re.search(r'(\d{4}-\d{2}-\d{2})', filepath.stem)
    if m:
        return date.fromisoformat(m.group(1))
    return date.fromtimestamp(filepath.stat().st_mtime)


def _parse_holdings_statement(filepath: Path) -> Union[List[RawHolding], str]:
    """
    Parse Zerodha 'Equity Holdings Statement as on YYYY-MM-DD' Excel format.
    Finds the header row dynamically, computes value = Qty Available × Prev Closing Price.
    """
    raw = pd.read_excel(filepath, sheet_name=0, header=None)

    # --- Extract report date from "Equity Holdings Statement as on YYYY-MM-DD" ---
    report_date: Optional[date] = None
    header_row_idx: Optional[int] = None

    for i, row in raw.iterrows():
        row_str = " ".join(str(v) for v in row if str(v) != "nan")
        # Date line
        m = re.search(r'as on (\d{4}-\d{2}-\d{2})', row_str)
        if m and report_date is None:
            report_date = date.fromisoformat(m.group(1))
        # Header row (contains 'Symbol' and 'Previous Closing Price')
        if "Symbol" in row_str and "Previous Closing Price" in row_str:
            header_row_idx = i

    if report_date is None:
        report_date = _parse_report_date_from_filename(filepath)
    if header_row_idx is None:
        return f"Zerodha parser: could not find data header row in {filepath.name}"

    # Re-read with the correct header row
    df = pd.read_excel(filepath, sheet_name=0, header=header_row_idx)
    df.columns = [str(c).strip() for c in df.columns]
    # Drop the unnamed first column (row index artifact)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    symbol_col = _find_col(list(df.columns), ["symbol"])
    isin_col = _find_col(list(df.columns), ["isin"])
    qty_col = _find_col(list(df.columns), ["quantity available", "quantity"])
    price_col = _find_col(list(df.columns), ["previous closing price", "ltp", "close price"])

    if not symbol_col or not qty_col or not price_col:
        return (
            f"Zerodha parser: missing columns in {filepath.name}. "
            f"Found: {list(df.columns)}"
        )

    holdings = []
    for _, row in df.iterrows():
        try:
            name = str(row[symbol_col]).strip()
            if not name or name.lower() in ("nan", "", "none"):
                continue

            qty_raw = row[qty_col]
            if pd.isna(qty_raw):
                continue
            units = float(qty_raw)
            if units <= 0:
                continue

            price_raw = row[price_col]
            if pd.isna(price_raw):
                continue
            price = float(price_raw)
            if price <= 0:
                continue

            value = units * price

            isin = None
            if isin_col:
                raw_isin = str(row[isin_col]).strip()
                if raw_isin and raw_isin.lower() not in ("nan", "none", ""):
                    isin = raw_isin

            holdings.append(RawHolding(
                report_date=report_date,
                asset_class="Stock",
                source="Zerodha",
                name=name,
                isin=isin,
                units=units,
                price=price,
                value=value,
                notes=None,
            ))
        except Exception:
            continue

    if not holdings:
        return f"Zerodha parser: no valid holdings found in {filepath.name}"
    return holdings


def _parse_simple_csv(filepath: Path) -> Union[List[RawHolding], str]:
    """Parse the simple Zerodha Holdings CSV (Instrument, Qty., LTP, Cur. val, ...)."""
    report_date = _parse_report_date_from_filename(filepath)
    suffix = filepath.suffix.lower()

    if suffix in ('.xlsx', '.xls'):
        df = pd.read_excel(filepath, sheet_name=0)
    else:
        df = pd.read_csv(filepath)

    df.columns = [str(c).strip() for c in df.columns]

    name_col = _find_col(list(df.columns), _NAME_ALIASES)
    units_col = _find_col(list(df.columns), _UNITS_ALIASES)
    price_col = _find_col(list(df.columns), _PRICE_ALIASES)
    value_col = _find_col(list(df.columns), _VALUE_ALIASES)

    if not name_col or not value_col:
        return (
            f"Zerodha parser: could not find required columns in {filepath.name}. "
            f"Found: {list(df.columns)}"
        )

    holdings = []
    for _, row in df.iterrows():
        try:
            name = str(row[name_col]).strip()
            if not name or name.lower() in ('nan', '', 'none'):
                continue

            raw_value = row[value_col]
            if pd.isna(raw_value):
                continue
            value = float(str(raw_value).replace(',', ''))
            if value <= 0:
                continue

            units = None
            if units_col:
                try:
                    u = row[units_col]
                    if pd.notna(u):
                        units = float(str(u).replace(',', ''))
                except Exception:
                    pass

            price = None
            if price_col:
                try:
                    p = row[price_col]
                    if pd.notna(p):
                        price = float(str(p).replace(',', ''))
                except Exception:
                    pass

            holdings.append(RawHolding(
                report_date=report_date,
                asset_class="Stock",
                source="Zerodha",
                name=name,
                isin=None,
                units=units,
                price=price,
                value=value,
                notes=None,
            ))
        except Exception:
            continue

    if not holdings:
        return f"Zerodha parser: no valid holdings found in {filepath.name}"
    return holdings


class ZerodhaParser(BaseHoldingParser):
    source = "Zerodha"
    asset_class = "Stock"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            suffix = filepath.suffix.lower()
            if suffix in ('.xlsx', '.xls'):
                # Peek to detect Holdings Statement format
                raw = pd.read_excel(filepath, sheet_name=0, header=None, nrows=25)
                content = " ".join(
                    str(v) for row in raw.values for v in row if str(v) != "nan"
                )
                if "Equity Holdings Statement" in content or "Previous Closing Price" in content:
                    return _parse_holdings_statement(filepath)
            # Fall through to simple CSV/Excel parser
            return _parse_simple_csv(filepath)
        except Exception as e:
            return f"Zerodha parser error ({filepath.name}): {e}"
