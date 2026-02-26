"""
SBI Bank Statement Parser
Supports CSV format
"""

import os
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseParser, RawTransaction


# ---------------------------------------------------------------------------
# Parser class (new architecture)
# ---------------------------------------------------------------------------

class SbiSavingsParser(BaseParser):
    account = "SBI Account"
    account_type = "savings"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        df = parse_sbi_csv(str(filepath))
        if isinstance(df, str):
            return df
        rows = []
        for _, row in df.iterrows():
            rows.append(RawTransaction(
                date=row["Date"].date() if hasattr(row["Date"], "date") else row["Date"],
                raw_description=str(row["Description"]),
                amount=float(row["Amount"]),
                type=str(row["Type"]),
                account=self.account,
                account_type=self.account_type,
            ))
        return rows


def parse_sbi_csv(filepath):
    """
    Parse SBI Bank statement CSV
    
    SBI CSV format has:
    - Multiple header rows with account info
    - Transaction header row with: Txn Date, Value Date, Description, 
      Ref No./Cheque No., Debit, Credit, Balance
    - Data rows starting immediately after the header
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        DataFrame with columns: Date, Description, Amount, Type, Source, File
        Or error message string if parsing fails
    """
    try:
        # Read the file to find the header row
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the row with "Txn Date"
        header_row_idx = None
        for i, line in enumerate(lines):
            if 'Txn Date' in line:
                header_row_idx = i
                break
        
        if header_row_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Header not found"
        
        # Read CSV with the header row as the column names
        # Use header=0 to treat the first row in skiprows result as header
        df = pd.read_csv(filepath, encoding='utf-8', skiprows=header_row_idx, 
                         on_bad_lines='skip', header=0)
        
        # Clean column names (remove extra spaces)
        df.columns = [str(col).strip() for col in df.columns]
        
        # Find columns - look for exact column names
        date_col = None
        desc_col = None
        debit_col = None
        credit_col = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'txn date' in col_lower or col_lower == 'txn date':
                date_col = col
            elif 'description' in col_lower:
                desc_col = col
            elif 'debit' in col_lower:
                debit_col = col
            elif 'credit' in col_lower and 'interest' not in col_lower:
                credit_col = col
        
        if not date_col or not desc_col:
            return f"Failed to parse {os.path.basename(filepath)}: Required columns not found (date: {date_col}, desc: {desc_col})"

        rows = []
        for idx, row in df.iterrows():
            try:
                # Get transaction date
                txn_date = str(row[date_col]).strip()
                
                # Skip invalid dates
                if not txn_date or txn_date in ['nan', '', 'None', 'Txn Date']:
                    continue
                
                # Get description
                description = str(row[desc_col]).strip()
                if description == 'nan':
                    description = ''
                
                # Get debit and credit amounts
                debit = 0.0
                credit = 0.0
                
                if debit_col:
                    debit_str = str(row[debit_col]).strip()
                    if debit_str and debit_str not in ['', 'nan', 'None']:
                        try:
                            # Remove commas and convert to float
                            debit = float(debit_str.replace(',', '').replace('"', ''))
                        except:
                            pass
                
                if credit_col:
                    credit_str = str(row[credit_col]).strip()
                    if credit_str and credit_str not in ['', 'nan', 'None']:
                        try:
                            # Remove commas and convert to float
                            credit = float(credit_str.replace(',', '').replace('"', ''))
                        except:
                            pass
                
                # Skip if no amount
                if debit == 0.0 and credit == 0.0:
                    continue
                
                # Determine amount and type
                amount = debit if debit > 0 else credit
                typ = "Debit" if debit > 0 else "Credit"
                
                rows.append({
                    "Date": pd.to_datetime(txn_date, dayfirst=True, errors='coerce'),
                    "Description": description,
                    "Amount": amount,
                    "Type": typ,
                    "Source": "SBI Account",
                    "File": os.path.basename(filepath)
                })
            except Exception as e:
                # Skip problematic rows
                continue
        
        if not rows:
            return f"Failed to parse {os.path.basename(filepath)}: No valid transactions found"
        
        result_df = pd.DataFrame(rows)
        # Filter out rows with invalid dates
        result_df = result_df[result_df['Date'].notna()]
        
        if result_df.empty:
            return f"Failed to parse {os.path.basename(filepath)}: No valid dates found"
        
        return result_df
        
    except Exception as e:
        return f"Failed to parse {os.path.basename(filepath)}: {str(e)}"

