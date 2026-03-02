"""
Vehicle Parser.
Reads simple key-value .txt files for vehicle holdings.

Expected file location: source_files/vehicles/
One file per vehicle. Update `value` and `date` whenever you want
to refresh the depreciated market valuation.

File format (all keys optional except `value`):
    name: Honda Elevate ZX DT
    year: 2024
    purchased: March 2024
    value: 1400000
    date: 2026-02-28
    notes: ~2 yr old. Source: Spinny/Cars24, Feb 2026
"""

from pathlib import Path
from typing import List, Union
from datetime import date

from .base import BaseHoldingParser, RawHolding


def _parse_vehicle_file(filepath: Path) -> Union[RawHolding, str]:
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
        return f"Vehicle parser: could not read {filepath.name}: {e}"

    if "value" not in fields:
        return f"Vehicle parser: 'value' key missing in {filepath.name}"

    try:
        value = float(fields["value"].replace(",", ""))
    except ValueError:
        return f"Vehicle parser: invalid value '{fields['value']}' in {filepath.name}"

    name = fields.get("name") or filepath.stem.replace("_", " ").title()

    report_date = date.today()
    if "date" in fields:
        try:
            report_date = date.fromisoformat(fields["date"])
        except ValueError:
            pass

    notes_parts = []
    if "year" in fields:
        notes_parts.append(fields["year"])
    if "purchased" in fields:
        notes_parts.append(f"bought {fields['purchased']}")
    if "notes" in fields:
        notes_parts.append(fields["notes"])
    notes = "; ".join(notes_parts) if notes_parts else None

    return RawHolding(
        report_date=report_date,
        asset_class="Vehicle",
        source="Vehicle",
        name=name,
        isin=None,
        units=None,
        price=None,
        value=value,
        notes=notes,
    )


class VehicleParser(BaseHoldingParser):
    source = "Vehicle"
    asset_class = "Vehicle"

    def parse(self, filepath: Path) -> Union[List[RawHolding], str]:
        try:
            if filepath.suffix.lower() != ".txt":
                return f"Vehicle parser: expected .txt file, got {filepath.name}"
            result = _parse_vehicle_file(filepath)
            if isinstance(result, str):
                return result
            return [result]
        except Exception as e:
            return f"Vehicle parser error ({filepath.name}): {e}"
