"""
MOFSL (Motilal Oswal) Holdings Parser.
Handles CSV and Excel exports from MOFSL.

Expected file location: source_files/mofsl/
Report date parsed from filename or file mtime.

Flexible column aliases handle MOFSL format variations.
"""

import re
from datetime import date
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseHoldingParser, RawHolding

_NAME_ALIASES = ["stock name", "scrip name", "scrip", "stock", "instrument", "name", "security name"]
_UNITS_ALIASES = ["quantity", "qty", "shares", "net qty", "net quantity", "balance qty"]
_PRICE_ALIASES = ["cmp", "ltp", "market price", "current price", "close price", "mkt price"]
_VALUE_ALIASES = ["current value", "market value", "cur value", "mkt value", "value (inr)", "total value"]


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


def _parse_report_date(filepath: Path) -> date:
    name = filepath.stem
    m = re.search(r'(\d{4}-\d{2}-\d{2})', name)
    if m:
        return date.fromisoformat(m.group(1))
    return date.fromtimestamp(filepath.stat().st_mtime)


class MofslParser(BaseHoldingParser):
    source = "MOFSL"
    asset_class = "Stock"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            report_date = _parse_report_date(filepath)
            suffix = filepath.suffix.lower()

            if suffix in ('.xlsx', '.xls'):
                df = pd.read_excel(filepath, sheet_name=0)
            elif suffix == '.csv':
                df = pd.read_csv(filepath)
            else:
                return f"MOFSL parser: unsupported file type {filepath.name}"

            df.columns = [str(c).strip() for c in df.columns]

            # Skip summary/footer rows (empty name or total rows)
            name_col = _find_col(list(df.columns), _NAME_ALIASES)
            units_col = _find_col(list(df.columns), _UNITS_ALIASES)
            price_col = _find_col(list(df.columns), _PRICE_ALIASES)
            value_col = _find_col(list(df.columns), _VALUE_ALIASES)

            if not name_col or not value_col:
                return (
                    f"MOFSL parser: could not find required columns in {filepath.name}. "
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
                    value_str = str(raw_value).replace(',', '').strip()
                    if not value_str or value_str.lower() in ('nan', ''):
                        continue
                    value = float(value_str)
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
                        asset_class=self.asset_class,
                        source=self.source,
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
                return f"MOFSL parser: no valid holdings found in {filepath.name}"

            return holdings

        except Exception as e:
            return f"MOFSL parser error ({filepath.name}): {e}"
