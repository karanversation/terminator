"""
Property Parser.
Reads simple key-value .txt files for real estate holdings.

Expected file location: source_files/property/
One file per property. Update `value` and `date` whenever you have
a fresh market valuation.

File format (all keys optional except `value`):
    name: Saya Zion, Gaur City 1
    area_sqft: 1660
    value: 16700000
    ownership_pct: 100       # your share of the property (default 100)
    outstanding_loan: 0      # outstanding loan principal in INR (default 0)
    date: 2026-02-28
    notes: 3 BHK, source: 99acres Feb 2026

The stored value = raw_value × (ownership_pct / 100) − outstanding_loan
"""

from datetime import date
from pathlib import Path
from typing import List, Union

from .base import BaseHoldingParser, RawHolding


def _parse_property_file(filepath: Path) -> Union[RawHolding, str]:
    """Parse a single property .txt file into a RawHolding."""
    fields = {}
    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, _, val = line.partition(":")
                    fields[key.strip().lower()] = val.strip()
    except Exception as e:
        return f"Property parser: could not read {filepath.name}: {e}"

    if "value" not in fields:
        return f"Property parser: 'value' key missing in {filepath.name}"

    try:
        raw_value = float(fields["value"].replace(",", ""))
    except ValueError:
        return f"Property parser: invalid value '{fields['value']}' in {filepath.name}"

    try:
        ownership_pct = float(fields.get("ownership_pct", "100").replace(",", ""))
    except ValueError:
        ownership_pct = 100.0

    try:
        outstanding_loan = float(fields.get("outstanding_loan", "0").replace(",", ""))
    except ValueError:
        outstanding_loan = 0.0

    net_value = round(raw_value * (ownership_pct / 100) - outstanding_loan, 2)

    # Name: from file or filename stem
    name = fields.get("name") or filepath.stem.replace("_", " ").title()

    # Date
    report_date = date.today()
    if "date" in fields:
        try:
            report_date = date.fromisoformat(fields["date"])
        except ValueError:
            pass

    notes_parts = []
    if "area_sqft" in fields:
        notes_parts.append(f"{fields['area_sqft']} sq ft")
    notes_parts.append(f"{ownership_pct:.0f}% ownership")
    if outstanding_loan > 0:
        notes_parts.append(f"₹{outstanding_loan:,.0f} loan outstanding")
    if fields.get("notes"):
        notes_parts.append(fields["notes"])
    notes = "; ".join(notes_parts) if notes_parts else None

    return RawHolding(
        report_date=report_date,
        asset_class="Property",
        source="Property",
        name=name,
        isin=None,
        units=None,
        price=None,
        value=net_value,
        notes=notes,
    )


class PropertyParser(BaseHoldingParser):
    source = "Property"
    asset_class = "Property"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            if filepath.suffix.lower() != ".txt":
                return f"Property parser: expected .txt file, got {filepath.name}"

            result = _parse_property_file(filepath)
            if isinstance(result, str):
                return result
            return [result]

        except Exception as e:
            return f"Property parser error ({filepath.name}): {e}"
