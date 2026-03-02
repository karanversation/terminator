"""
CAMS Consolidated Account Statement (CAS) PDF Parser.
Handles password-protected PDFs from CAMS / KFintech.

Expected file location: source_files/cams/
Password: configured via CAMS_PDF_PASSWORD constant.

Extracts per-fund holdings from "Closing Unit Balance" lines,
matching each to the fund name/ISIN captured earlier in the text.
Report date = end date of the statement period.
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

from .base import BaseHoldingParser, RawHolding

import os as _os

# Regex: fund scheme line — variable-length code, name up to first ( or -,
# then somewhere later: ISIN: INFxxx
_FUND_NAME_RE = re.compile(
    r'^[A-Z0-9]{2,10}-(.+?)\s*[\(-].*ISIN:\s*(INF\w+)',
    re.IGNORECASE,
)

# Regex: Closing Unit Balance line
_CLOSING_RE = re.compile(
    r'Closing Unit Balance:\s*([\d,]+\.?\d*)'
    r'\s+NAV on\s+(\d{2}-\w+-\d{4}):\s+INR\s+([\d,]+\.?\d+)'
    r'\s+Total Cost Value:\s+[\d,]+\.?\d+'
    r'\s+Market Value on\s+\d{2}-\w+-\d{4}:\s+INR\s+([\d,]+\.?\d+)'
)

# Regex: statement period end date
_PERIOD_RE = re.compile(r'\d{2}-\w+-\d{4}\s+To\s+(\d{2}-\w+-\d{4})')

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def _parse_dd_mon_yyyy(s: str) -> Optional[date]:
    try:
        parts = s.strip().split('-')
        return date(int(parts[2]), _MONTH_MAP[parts[1].lower()[:3]], int(parts[0]))
    except Exception:
        return None


class CamsParser(BaseHoldingParser):
    source = "CAMS CAS"
    asset_class = "Mutual Fund"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            import pdfplumber
        except ImportError:
            return "cams parser: pdfplumber not installed. Run: pip install pdfplumber"

        try:
            suffix = filepath.suffix.lower()
            if suffix != '.pdf':
                return f"CAMS parser: expected PDF, got {filepath.name}"

            password = _os.environ.get("CAMS_PDF_PASSWORD", "")
            if not password:
                return (
                    f"CAMS parser: CAMS_PDF_PASSWORD is not set ({filepath.name}). "
                    "Add it to .streamlit/secrets.toml:\n  CAMS_PDF_PASSWORD = \"YOUR_PAN\""
                )

            with pdfplumber.open(filepath, password=password) as pdf:
                full_text = '\n'.join(p.extract_text() or '' for p in pdf.pages)

            # Extract statement end date (report date)
            report_date: Optional[date] = None
            m = _PERIOD_RE.search(full_text)
            if m:
                report_date = _parse_dd_mon_yyyy(m.group(1))
            if report_date is None:
                return f"CAMS parser: could not find statement period in {filepath.name}"

            # Scan lines: track current fund, emit holding on closing balance line
            current_fund = None
            current_isin = None
            holdings: List[RawHolding] = []

            for line in full_text.splitlines():
                fm = _FUND_NAME_RE.match(line.strip())
                if fm:
                    current_fund = fm.group(1).strip()
                    current_isin = fm.group(2).strip()

                cm = _CLOSING_RE.search(line)
                if cm and current_fund:
                    units = float(cm.group(1).replace(',', ''))
                    nav = float(cm.group(3).replace(',', ''))
                    value = float(cm.group(4).replace(',', ''))

                    holdings.append(RawHolding(
                        report_date=report_date,
                        asset_class=self.asset_class,
                        source=self.source,
                        name=current_fund,
                        isin=current_isin,
                        units=units,
                        price=nav,
                        value=value,
                        notes=None,
                    ))

            if not holdings:
                return f"CAMS parser: no holdings found in {filepath.name}"

            return holdings

        except Exception as e:
            return f"CAMS parser error ({filepath.name}): {e}"
