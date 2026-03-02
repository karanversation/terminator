"""
Liability Parser.
Reads simple key-value .txt files for loans and credit obligations.

Expected file location: source_files/liabilities/
One file per liability. Update `value` and `date` to reflect outstanding principal.

File format (all keys optional except `value`):
    name: Home Loan - Saya Zion
    value: 5000000       # outstanding principal in INR
    date: 2026-02-28
    notes: SBI home loan at 8.5% p.a., EMI ₹45,000/month

Values are stored as positive numbers in the DB.
The UI subtracts liabilities from the total networth.
"""

from pathlib import Path
from typing import List, Union
from datetime import date

from .base import BaseHoldingParser, RawHolding


def _parse_liability_file(filepath: Path) -> Union[RawHolding, str]:
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
        return f"Liability parser: could not read {filepath.name}: {e}"

    if "value" not in fields:
        return f"Liability parser: 'value' key missing in {filepath.name}"

    try:
        value = float(fields["value"].replace(",", ""))
    except ValueError:
        return f"Liability parser: invalid value '{fields['value']}' in {filepath.name}"

    name = fields.get("name") or filepath.stem.replace("_", " ").title()

    report_date = date.today()
    if "date" in fields:
        try:
            report_date = date.fromisoformat(fields["date"])
        except ValueError:
            pass

    notes = fields.get("notes") or None

    return RawHolding(
        report_date=report_date,
        asset_class="Liability",
        source="Liability",
        name=name,
        isin=None,
        units=None,
        price=None,
        value=value,
        notes=notes,
    )


class LiabilityParser(BaseHoldingParser):
    source = "Liability"
    asset_class = "Liability"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            if filepath.suffix.lower() != ".txt":
                return f"Liability parser: expected .txt file, got {filepath.name}"
            result = _parse_liability_file(filepath)
            if isinstance(result, str):
                return result
            return [result]
        except Exception as e:
            return f"Liability parser error ({filepath.name}): {e}"
