"""
HDFC Bank Statement Parsers
Supports both Credit Card CSV and Savings Account TXT formats
"""

import os
import re
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseParser, RawTransaction


# ---------------------------------------------------------------------------
# Parser classes (new architecture)
# ---------------------------------------------------------------------------

class HdfcDinersParser(BaseParser):
    account = "HDFC Diners Black CC"
    account_type = "credit_card"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        df = parse_hdfc_cc_csv(str(filepath), account_override=self.account)
        if isinstance(df, str):
            return df
        return _df_to_raw(df, self.account, self.account_type)


class HdfcRegaliaParser(BaseParser):
    account = "HDFC Regalia CC"
    account_type = "credit_card"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        df = parse_hdfc_cc_csv(str(filepath), account_override=self.account)
        if isinstance(df, str):
            return df
        return _df_to_raw(df, self.account, self.account_type)


class HdfcSavingsParser(BaseParser):
    account = "HDFC Savings Account"
    account_type = "savings"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        df = parse_hdfc_savings_txt(str(filepath))
        if isinstance(df, str):
            return df
        return _df_to_raw(df, self.account, self.account_type)


def _df_to_raw(df: pd.DataFrame, account: str, account_type: str) -> list:
    rows = []
    for _, row in df.iterrows():
        rows.append(RawTransaction(
            date=row["Date"].date() if hasattr(row["Date"], "date") else row["Date"],
            raw_description=str(row["Description"]),
            amount=float(row["Amount"]),
            type=str(row["Type"]),
            account=account,
            account_type=account_type,
        ))
    return rows


def parse_hdfc_cc_csv(filepath, account_override=None):
    """
    Parse HDFC Credit Card CSV (Diners Black & Regalia)

    Args:
        filepath: Path to the CSV file
        account_override: If provided, use this as the Source instead of inferring from filename

    Returns:
        DataFrame with columns: Date, Description, Amount, Type, Source, File
        Or error message string if parsing fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find the transaction header line
        header_line_idx = None
        for i, line in enumerate(lines):
            if line.startswith("Transaction type~Primary"):
                header_line_idx = i
                break

        if header_line_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Header not found"

        headers = lines[header_line_idx].strip().split("~")
        data_lines = lines[header_line_idx + 1:]

        rows = []
        file_name = os.path.basename(filepath)
        if account_override:
            card_type = account_override
        else:
            card_type = "HDFC Diners Black CC" if "2508" in file_name else "HDFC Regalia CC"
        
        for line in data_lines:
            line = line.strip()
            if not line or line.startswith("Opening Bal") or line.startswith("Programms"):
                continue
            
            cols = line.split("~")
            if len(cols) < len(headers):
                continue
            
            row = dict(zip(headers, cols))
            
            # Skip non-transaction rows
            if not row.get("DATE") or not row.get("AMT"):
                continue
            
            # Parse date
            date_str = row.get("DATE", "")
            try:
                # Handle date with time
                if " " in date_str:
                    date_str = date_str.split(" ")[0]
                parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            except:
                parsed_date = pd.NaT
            
            # Parse amount
            amt_str = row.get("AMT", "0").replace(',', '').strip()
            try:
                amount = float(amt_str) if amt_str else 0.0
            except:
                amount = 0.0
            
            # Skip zero amounts
            if amount == 0.0:
                continue
            
            # Determine if it's credit or debit
            is_credit = row.get("Debit / Credit", "").strip().lower() == "cr"
            
            rows.append({
                "Date": parsed_date,
                "Description": row.get("Description", "").strip(),
                "Amount": amount,
                "Type": "Credit" if is_credit else "Debit",
                "Source": card_type,
                "File": file_name
            })

        df = pd.DataFrame(rows)
        return df[df['Date'].notna()]  # Filter out invalid dates
    except Exception as e:
        return f"Failed to parse {os.path.basename(filepath)}: {str(e)}"


def parse_hdfc_savings_txt(filepath):
    """
    Parse HDFC Savings Account TXT using fixed-width format
    
    Args:
        filepath: Path to the TXT file
        
    Returns:
        DataFrame with columns: Date, Description, Amount, Type, Source, File
        Or error message string if parsing fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        rows = []
        date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2,4}')
        
        # Find column positions from the separator line (dashes)
        separator_line = None
        for line in lines:
            if '--------' in line and 'Withdrawal' not in line:
                separator_line = line
                break
        
        # Default column positions (based on typical HDFC statement format)
        withdrawal_col_start = 80
        withdrawal_col_end = 98
        deposit_col_start = 100
        deposit_col_end = 118
        
        if separator_line:
            # Find positions of amount columns from the separator
            try:
                # Look for consecutive dashes that represent the columns
                dash_groups = []
                in_dash = False
                start_pos = 0
                for i, char in enumerate(separator_line):
                    if char == '-':
                        if not in_dash:
                            start_pos = i
                            in_dash = True
                    else:
                        if in_dash:
                            dash_groups.append((start_pos, i))
                            in_dash = False
                if in_dash:
                    dash_groups.append((start_pos, len(separator_line)))
                
                # The last 3 dash groups should be: Withdrawal, Deposit, Balance
                if len(dash_groups) >= 3:
                    withdrawal_col_start, withdrawal_col_end = dash_groups[-3]
                    deposit_col_start, deposit_col_end = dash_groups[-2]
            except:
                pass  # Use default positions
        
        for i, line in enumerate(lines):
            if date_pattern.match(line.strip()):
                try:
                    date_str = line[:8].strip()
                    narration = line[10:52].strip()
                    
                    # Extract withdrawal and deposit amounts using column positions
                    withdrawal_str = line[withdrawal_col_start:withdrawal_col_end].strip().replace(',', '') if len(line) > withdrawal_col_end else ''
                    deposit_str = line[deposit_col_start:deposit_col_end].strip().replace(',', '') if len(line) > deposit_col_end else ''
                    
                    withdrawal_amt = 0
                    deposit_amt = 0
                    
                    # Parse withdrawal amount
                    if withdrawal_str and withdrawal_str.replace('.', '').replace('-', '').isdigit():
                        try:
                            withdrawal_amt = float(withdrawal_str)
                        except:
                            pass
                    
                    # Parse deposit amount
                    if deposit_str and deposit_str.replace('.', '').replace('-', '').isdigit():
                        try:
                            deposit_amt = float(deposit_str)
                        except:
                            pass
                    
                    # Determine transaction type and amount
                    if withdrawal_amt > 0 and deposit_amt == 0:
                        amount = withdrawal_amt
                        typ = "Debit"
                    elif deposit_amt > 0 and withdrawal_amt == 0:
                        amount = deposit_amt
                        typ = "Credit"
                    elif withdrawal_amt > 0 and deposit_amt > 0:
                        # Both present - unusual, but take the larger one
                        if withdrawal_amt >= deposit_amt:
                            amount = withdrawal_amt
                            typ = "Debit"
                        else:
                            amount = deposit_amt
                            typ = "Credit"
                    else:
                        continue  # No valid amount
                    
                    if amount <= 0:
                        continue
                    
                    rows.append({
                        "Date": pd.to_datetime(date_str, dayfirst=True, errors='coerce'),
                        "Description": narration,
                        "Amount": amount,
                        "Type": typ,
                        "Source": "HDFC Savings Account",
                        "File": os.path.basename(filepath)
                    })
                except Exception as e:
                    continue
        
        df = pd.DataFrame(rows)
        return df[df['Date'].notna()]  # Filter out invalid dates
    except Exception as e:
        return f"Failed to parse {os.path.basename(filepath)}: {str(e)}"

