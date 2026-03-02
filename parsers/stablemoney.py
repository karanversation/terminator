"""
Stable Money Portfolio Parser.
Handles CSV/Excel and PDF exports from Stable Money (bonds and FDs).

Expected file location: source_files/stablemoney/

PDF format: "Consolidated Investment Report" from stablebonds.in.
  - Report Generation Date used as report_date.
  - Buy transactions parsed from TRANSACTIONS SUMMARY section.
  - Bonds whose maturity date (embedded in name, e.g. "Jun'26") is before
    the report date are excluded (already matured/repaid).
  - Total Value (INR) at purchase used as the holding value (bonds trade
    close to face value so this is a good approximation).
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

# ---------------------------------------------------------------------------
# CSV / Excel support (kept for future use)
# ---------------------------------------------------------------------------

_NAME_ALIASES = ["instrument", "bond name", "name", "security name", "scheme name", "issuer"]
_TYPE_ALIASES = ["type", "asset type", "instrument type", "category"]
_VALUE_ALIASES = ["current value", "invested value", "market value", "value", "amount"]
_MATURITY_ALIASES = ["maturity date", "maturity", "due date", "end date"]
_COUPON_ALIASES = ["coupon rate", "interest rate", "rate", "yield", "coupon"]
_UNITS_ALIASES = ["units", "quantity", "qty", "bonds"]
_PRICE_ALIASES = ["price", "face value", "nav"]

_TYPE_MAP = {
    "bond": "Bond", "bonds": "Bond", "fd": "FD", "fixed deposit": "FD",
    "sgb": "Bond", "sovereign gold bond": "Bond", "corporate bond": "Bond",
    "g-sec": "Bond", "gsec": "Bond", "t-bill": "Bond", "tbill": "Bond", "ncd": "Bond",
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


def _normalize_asset_class(raw_type: str) -> str:
    if not raw_type or raw_type.lower() in ('nan', '', 'none'):
        return "Bond"
    return _TYPE_MAP.get(raw_type.lower().strip(), "Bond")


def _parse_report_date(filepath: Path) -> date:
    name = filepath.stem
    m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    if m:
        return date.fromisoformat(m.group(1))
    return date.fromtimestamp(filepath.stat().st_mtime)


# ---------------------------------------------------------------------------
# PDF support — stablebonds.in Consolidated Investment Report
# ---------------------------------------------------------------------------

_REPORT_DATE_RE = re.compile(
    r'Report Generation Date:\s*(\d{1,2})-(\w{3})-(\d{4})'
)

# Buy transaction row:
# 2026-02-18 INE1VXE07015 STL Networks LimitedSept'27 Buy 5 98,537.71 492,688.57 ...
_BUY_ROW_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2})\s+'    # date
    r'(IN[A-Z0-9]{10})\s+'        # ISIN
    r'(.+?)\s+Buy\s+'             # bond name (lazy, up to "Buy")
    r'([\d,]+)\s+'                # quantity
    r'[\d,.]+\s+'                 # price/unit (skip)
    r'([\d,.]+)'                  # total value (INR)
)

# Maturity month+year embedded in bond name: "Jun'26", "Sept'27", "Dec'26"
_MATURITY_IN_NAME_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|June?|July?|Aug|Sep|Sept|Oct|Nov|Dec)'(\d{2})",
    re.IGNORECASE,
)

_MONTH_ABB = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5,
    'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def _parse_gen_date(day: str, mon: str, year: str) -> Optional[date]:
    try:
        m = _MONTH_ABB.get(mon.lower())
        if m:
            return date(int(year), m, int(day))
    except Exception:
        pass
    return None


def _maturity_date(bond_name: str) -> Optional[date]:
    """Extract maturity date from bond name like 'Muthoot Capital Jun\'26'."""
    m = _MATURITY_IN_NAME_RE.search(bond_name)
    if not m:
        return None
    try:
        month = _MONTH_ABB.get(m.group(1).lower())
        year = 2000 + int(m.group(2))
        # Use last day of that month as maturity (conservative)
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)
    except Exception:
        return None


def _parse_stablemoney_pdf(filepath: Path) -> Union[List[RawHolding], str]:
    """Parse a Stable Money Consolidated Investment Report PDF."""
    try:
        import pdfplumber
    except ImportError:
        return "Stable Money PDF parser: pdfplumber not installed. Run: pip install pdfplumber"

    try:
        with pdfplumber.open(filepath) as pdf:
            full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    except Exception as e:
        return f"Stable Money PDF parser: could not open {filepath.name}: {e}"

    # Extract report generation date
    report_date: Optional[date] = None
    m = _REPORT_DATE_RE.search(full_text)
    if m:
        report_date = _parse_gen_date(m.group(1), m.group(2), m.group(3))
    if report_date is None:
        report_date = _parse_report_date(filepath)

    # Parse buy transactions; skip those already matured as of report_date
    holdings: List[RawHolding] = []
    seen_isins = set()

    for line in full_text.splitlines():
        line = line.strip()
        rm = _BUY_ROW_RE.match(line)
        if not rm:
            continue

        isin = rm.group(2)
        if isin in seen_isins:
            continue  # keep first (most recent) buy if ISIN appears twice

        bond_name = rm.group(3).strip()
        quantity = float(rm.group(4).replace(',', ''))
        total_value = float(rm.group(5).replace(',', ''))

        # Skip if bond has already matured by the report date
        mat = _maturity_date(bond_name)
        if mat and mat < report_date:
            continue

        seen_isins.add(isin)
        notes = f"Maturity: {mat.strftime('%b %Y')}" if mat else None

        holdings.append(RawHolding(
            report_date=report_date,
            asset_class="Bond",
            source="Stable Money",
            name=bond_name,
            isin=isin,
            units=quantity,
            price=None,
            value=total_value,
            notes=notes,
        ))

    # An empty list is valid — all bonds in this report may have already matured
    return holdings


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class StableMoneyParser(BaseHoldingParser):
    source = "Stable Money"
    asset_class = "Bond"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            suffix = filepath.suffix.lower()

            if suffix == '.pdf':
                return _parse_stablemoney_pdf(filepath)

            report_date = _parse_report_date(filepath)

            if suffix in ('.xlsx', '.xls'):
                df = pd.read_excel(filepath, sheet_name=0)
            elif suffix == '.csv':
                df = pd.read_csv(filepath)
            else:
                return f"Stable Money parser: unsupported file type {filepath.name}"

            df.columns = [str(c).strip() for c in df.columns]

            name_col = _find_col(list(df.columns), _NAME_ALIASES)
            type_col = _find_col(list(df.columns), _TYPE_ALIASES)
            value_col = _find_col(list(df.columns), _VALUE_ALIASES)
            maturity_col = _find_col(list(df.columns), _MATURITY_ALIASES)
            coupon_col = _find_col(list(df.columns), _COUPON_ALIASES)
            units_col = _find_col(list(df.columns), _UNITS_ALIASES)
            price_col = _find_col(list(df.columns), _PRICE_ALIASES)

            if not name_col or not value_col:
                return (
                    f"Stable Money parser: could not find required columns in {filepath.name}. "
                    f"Found: {list(df.columns)}"
                )

            holdings = []
            for _, row in df.iterrows():
                try:
                    name = str(row[name_col]).strip()
                    if not name or name.lower() in ('nan', '', 'none', 'total'):
                        continue

                    raw_value = row[value_col]
                    if pd.isna(raw_value):
                        continue
                    value = float(str(raw_value).replace(',', '').replace('₹', '').strip())
                    if value <= 0:
                        continue

                    asset_class = self.asset_class
                    if type_col:
                        asset_class = _normalize_asset_class(str(row[type_col]))

                    notes_parts = []
                    if maturity_col:
                        mat = str(row[maturity_col]).strip()
                        if mat and mat.lower() not in ('nan', '', 'none'):
                            notes_parts.append(f"Maturity: {mat}")
                    if coupon_col:
                        coupon = str(row[coupon_col]).strip()
                        if coupon and coupon.lower() not in ('nan', '', 'none'):
                            notes_parts.append(f"Rate: {coupon}")
                    notes = "; ".join(notes_parts) if notes_parts else None

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
                        isin=None,
                        units=units,
                        price=price,
                        value=value,
                        notes=notes,
                    ))
                except Exception:
                    continue

            if not holdings:
                return f"Stable Money parser: no valid holdings found in {filepath.name}"

            return holdings

        except Exception as e:
            return f"Stable Money parser error ({filepath.name}): {e}"
