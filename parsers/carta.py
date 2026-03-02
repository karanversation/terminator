"""
Carta ESOP Parser.
Handles exerciseHistory.csv exports from Carta (carta.com).

Expected file location: source_files/carta/

Reads exercise history to derive current share holdings per company.
Shares are grouped by company; the most recent Fair Market Value (FMV)
in the file is used as the current price per share.

Private company shares are priced in USD — converted to INR using
CARTA_USD_INR_RATE. Update this constant when you have a newer FMV or
want to reflect a different exchange rate.
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

# USD → INR conversion rate for Carta private-company shares.
# Update to the approximate rate on your valuation date.
CARTA_USD_INR_RATE = 91.08

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

# Parses "Dec. 21, 2021" or "Jan. 23, 2024"
_DATE_RE = re.compile(r'(\w+)\.?\s+(\d{1,2}),\s*(\d{4})')

# Parses "$4.02 USD" or "$0.3425 USD"
_USD_RE = re.compile(r'\$([0-9,.]+)\s*USD', re.IGNORECASE)

# Parses "5000 NSO" or "15000 ISO"
_SHARES_RE = re.compile(r'([\d,]+)\s*(?:NSO|ISO|RSA|RSU)?', re.IGNORECASE)


def _parse_carta_date(s: str) -> Optional[date]:
    m = _DATE_RE.search(str(s))
    if not m:
        return None
    try:
        month = _MONTH_MAP.get(m.group(1).lower()[:3])
        if month:
            return date(int(m.group(3)), month, int(m.group(2)))
    except Exception:
        pass
    return None


def _parse_usd(s: str) -> Optional[float]:
    m = _USD_RE.search(str(s))
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except Exception:
            pass
    return None


def _parse_shares(s: str) -> Optional[float]:
    m = _SHARES_RE.match(str(s).strip())
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except Exception:
            pass
    return None


class CartaParser(BaseHoldingParser):
    source = "Carta"
    asset_class = "ESOP"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            suffix = filepath.suffix.lower()
            if suffix != '.csv':
                return f"Carta parser: expected CSV, got {filepath.name}"

            df = pd.read_csv(filepath)
            df.columns = [str(c).strip() for c in df.columns]

            required = {'Issued by', 'Submission date', 'Fair market value', 'Shares'}
            missing = required - set(df.columns)
            if missing:
                return (
                    f"Carta parser: missing columns {missing} in {filepath.name}. "
                    f"Found: {list(df.columns)}"
                )

            # Parse each row
            rows = []
            for _, row in df.iterrows():
                company = str(row['Issued by']).strip()
                if not company or company.lower() in ('nan', '', 'none'):
                    continue

                sub_date = _parse_carta_date(row['Submission date'])
                fmv = _parse_usd(row['Fair market value'])
                shares = _parse_shares(row['Shares'])

                if not sub_date or fmv is None or shares is None:
                    continue

                rows.append({
                    'company': company,
                    'date': sub_date,
                    'fmv': fmv,
                    'shares': shares,
                })

            if not rows:
                return f"Carta parser: no valid rows found in {filepath.name}"

            # Group by company: sum shares, use latest FMV + date
            companies = {}
            for r in rows:
                c = r['company']
                if c not in companies:
                    companies[c] = {'total_shares': 0.0, 'latest_fmv': 0.0, 'latest_date': None}
                companies[c]['total_shares'] += r['shares']
                if companies[c]['latest_date'] is None or r['date'] > companies[c]['latest_date']:
                    companies[c]['latest_fmv'] = r['fmv']
                    companies[c]['latest_date'] = r['date']

            holdings = []
            for company, data in companies.items():
                total_shares = data['total_shares']
                fmv_usd = data['latest_fmv']
                fmv_date = data['latest_date']

                value_usd = total_shares * fmv_usd
                value_inr = round(value_usd * CARTA_USD_INR_RATE, 2)
                price_inr = round(fmv_usd * CARTA_USD_INR_RATE, 2)

                holdings.append(RawHolding(
                    report_date=fmv_date,
                    asset_class="ESOP",
                    source=self.source,
                    name=company,
                    isin=None,
                    units=total_shares,
                    price=price_inr,
                    value=value_inr,
                    notes=(
                        f"FMV ${fmv_usd}/share as of {fmv_date.strftime('%b %Y')}; "
                        f"USD ${value_usd:,.0f} @ ₹{CARTA_USD_INR_RATE}/USD"
                    ),
                ))

            return holdings

        except Exception as e:
            return f"Carta parser error ({filepath.name}): {e}"
