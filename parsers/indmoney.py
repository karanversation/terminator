"""
IndMoney Holdings Parser.
Handles mixed-type portfolio exports from IndMoney.

Supported formats:
  - CSV / Excel (generic holdings export)
  - PDF (IndMoney Global IFSC account statement from DriveWealth — US stocks)

Expected file location: source_files/indmoney/
Report date: end date of statement period (PDF) or filename/mtime (CSV/Excel).

US stock values in the PDF are in USD and converted to INR using
INDMONEY_USD_INR_RATE. Update this constant to match the rate on the
statement date.
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

# USD → INR conversion rate for IndMoney Global (US stocks) PDF statements.
# Update to the approximate rate on your statement date.
INDMONEY_USD_INR_RATE = 91.08

_NAME_ALIASES = ["name", "instrument", "stock", "fund name", "scheme name", "security"]
_TYPE_ALIASES = ["asset type", "type", "asset class", "category"]
_ISIN_ALIASES = ["isin"]
_UNITS_ALIASES = ["units", "quantity", "qty", "shares"]
_PRICE_ALIASES = ["ltp", "nav", "current price", "market price", "price"]
_VALUE_ALIASES = ["current value", "market value", "value", "total value", "cur value"]

# Mapping from IndMoney type strings to our asset classes
_TYPE_MAP = {
    "stock": "Stock",
    "equity": "Stock",
    "mutual fund": "Mutual Fund",
    "mf": "Mutual Fund",
    "bond": "Bond",
    "fd": "FD",
    "fixed deposit": "FD",
    "etf": "Stock",
    "us stocks": "Stock",
    "us stock": "Stock",
}


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


def _detect_asset_class_from_isin(isin: str) -> str:
    isin = str(isin).strip().upper()
    if isin.startswith("INF"):
        return "Mutual Fund"
    return "Stock"


def _normalize_asset_class(raw_type: str) -> str:
    if not raw_type or raw_type.lower() in ('nan', '', 'none'):
        return "Stock"
    return _TYPE_MAP.get(raw_type.lower().strip(), "Stock")


def _parse_report_date(filepath: Path) -> date:
    name = filepath.stem
    m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    if m:
        return date.fromisoformat(m.group(1))
    return date.fromtimestamp(filepath.stat().st_mtime)


# ---------------------------------------------------------------------------
# DriveWealth / IndMoney Global PDF — US stocks statement
# ---------------------------------------------------------------------------

# Regex: "January 01, 2026 - January 31, 2026" → end date
_PDF_PERIOD_RE = re.compile(
    r'\w+ \d{1,2},\s*\d{4}\s*[-–]\s*(\w+)\s+(\d{1,2}),\s*(\d{4})'
)

# Holdings data row: ends with 7 numeric tokens + 1 A/C type letter
# e.g.: ADOBE INC COM ADBE 3.29029539 399.89 1,315.76 293.25 964.88 (350.88) C
_HOLDINGS_ROW_RE = re.compile(
    r'^(.+?)\s+'                   # description (lazy)
    r'([A-Z]{2,6})\s+'             # symbol
    r'([\d.]+)\s+'                 # quantity
    r'[\d,.]+\s+'                  # unit cost
    r'[\d,.]+\s+'                  # total cost
    r'([\d,.]+)\s+'                # market price (USD)
    r'([\d,.]+)\s+'                # market value (USD)
    r'\(?[\d,.]+\)?\s+'            # gain/loss
    r'[A-Z]$'                      # A/C type
)

_MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

# Symbols to skip (cash sweep, money market)
_SKIP_SYMBOLS = {'DWBDS', 'MMDA', 'CASH'}


def _parse_indmoney_pdf(filepath: Path) -> Union[List[RawHolding], str]:
    """Parse IndMoney Global IFSC PDF statement (DriveWealth, US stocks)."""
    try:
        import pdfplumber
    except ImportError:
        return "IndMoney PDF parser: pdfplumber not installed. Run: pip install pdfplumber"

    try:
        with pdfplumber.open(filepath) as pdf:
            full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    except Exception as e:
        return f"IndMoney PDF parser: could not open {filepath.name}: {e}"

    # Extract report date from period line
    report_date: Optional[date] = None
    m = _PDF_PERIOD_RE.search(full_text)
    if m:
        try:
            month = _MONTH_NAMES.get(m.group(1).lower())
            report_date = date(int(m.group(3)), month, int(m.group(2)))
        except Exception:
            pass
    if report_date is None:
        report_date = _parse_report_date(filepath)

    # Parse holdings rows from HOLDINGS section
    in_holdings = False
    holdings: List[RawHolding] = []

    for line in full_text.splitlines():
        line = line.strip()
        if line == 'HOLDINGS':
            in_holdings = True
            continue
        if line == 'ACTIVITY':
            in_holdings = False
            continue
        if not in_holdings:
            continue

        rm = _HOLDINGS_ROW_RE.match(line)
        if not rm:
            continue

        symbol = rm.group(2)
        if symbol in _SKIP_SYMBOLS:
            continue

        description = rm.group(1).strip()
        units = float(rm.group(3).replace(',', ''))
        price_usd = float(rm.group(4).replace(',', ''))
        value_usd = float(rm.group(5).replace(',', ''))

        # Convert USD → INR
        price_inr = round(price_usd * INDMONEY_USD_INR_RATE, 2)
        value_inr = round(value_usd * INDMONEY_USD_INR_RATE, 2)

        holdings.append(RawHolding(
            report_date=report_date,
            asset_class="Stock",
            source="IndMoney",
            name=f"{description} ({symbol})",
            isin=symbol,
            units=units,
            price=price_inr,
            value=value_inr,
            notes=f"USD ${value_usd:,.2f} @ ₹{INDMONEY_USD_INR_RATE}/USD",
        ))

    if not holdings:
        return f"IndMoney PDF parser: no equity holdings found in {filepath.name}"

    return holdings


class IndmoneyParser(BaseHoldingParser):
    source = "IndMoney"
    asset_class = "Stock"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            suffix = filepath.suffix.lower()

            if suffix == '.pdf':
                return _parse_indmoney_pdf(filepath)

            report_date = _parse_report_date(filepath)

            if suffix in ('.xlsx', '.xls'):
                df = pd.read_excel(filepath, sheet_name=0)
            elif suffix == '.csv':
                df = pd.read_csv(filepath)
            else:
                return f"IndMoney parser: unsupported file type {filepath.name}"

            df.columns = [str(c).strip() for c in df.columns]

            name_col = _find_col(list(df.columns), _NAME_ALIASES)
            type_col = _find_col(list(df.columns), _TYPE_ALIASES)
            isin_col = _find_col(list(df.columns), _ISIN_ALIASES)
            units_col = _find_col(list(df.columns), _UNITS_ALIASES)
            price_col = _find_col(list(df.columns), _PRICE_ALIASES)
            value_col = _find_col(list(df.columns), _VALUE_ALIASES)

            if not name_col or not value_col:
                return (
                    f"IndMoney parser: could not find required columns in {filepath.name}. "
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

                    # Determine asset class
                    if type_col:
                        asset_class = _normalize_asset_class(str(row[type_col]))
                    elif isin_col:
                        isin = str(row[isin_col]).strip()
                        asset_class = _detect_asset_class_from_isin(isin)
                    else:
                        asset_class = self.asset_class

                    isin = None
                    if isin_col:
                        raw_isin = str(row[isin_col]).strip()
                        if raw_isin and raw_isin.lower() not in ('nan', 'none', ''):
                            isin = raw_isin

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
                        asset_class=asset_class,
                        source=self.source,
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
                return f"IndMoney parser: no valid holdings found in {filepath.name}"

            return holdings

        except Exception as e:
            return f"IndMoney parser error ({filepath.name}): {e}"
