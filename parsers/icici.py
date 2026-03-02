"""
ICICI Bank Statement Parser
Supports CSV format for both Savings Account and Credit Card
"""

import os
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseParser, RawTransaction


# ---------------------------------------------------------------------------
# Parser classes (new architecture)
# ---------------------------------------------------------------------------

class IciciSavingsParser(BaseParser):
    account = "ICICI Savings Account"
    account_type = "savings"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        suffix = Path(filepath).suffix.lower()
        if suffix in ('.xls', '.xlsx'):
            df = _parse_icici_as_excel(filepath)
        else:
            df = parse_icici_csv(str(filepath))
        if isinstance(df, str):
            return df
        return _df_to_raw(df, self.account, self.account_type)

    def get_closing_balance(self, filepath: Path):
        """Return (report_date, closing_balance) from the last valid transaction row."""
        suffix = filepath.suffix.lower()
        if suffix in ('.xls', '.xlsx'):
            df = _parse_icici_as_excel(filepath)
        else:
            df = _read_icici_csv_as_df(filepath)
        if isinstance(df, str):
            raise ValueError(df)

        for _, row in df[::-1].iterrows():
            try:
                date_str = str(row['Transaction Date']).strip()
                if not date_str or date_str in ['nan', '', 'None']:
                    continue
                bal_val = row.get('_balance')
                if bal_val is None or pd.isna(bal_val):
                    continue
                parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                if pd.isna(parsed_date):
                    continue
                return parsed_date.date(), float(bal_val)
            except Exception:
                continue

        raise ValueError(f"Could not extract closing balance from {filepath.name}")


class IciciCCParser(BaseParser):
    account = "ICICI Amazon Pay CC"
    account_type = "credit_card"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        df = parse_icici_cc_csv(str(filepath))
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
            raw_line=str(row.get("RawLine", "")),
        ))
    return rows


def _find_icici_header_row_excel(filepath):
    """Scan an ICICI XLS/XLSX to find the row index of the transaction header."""
    raw = pd.read_excel(filepath, header=None)
    for i, row in raw.iterrows():
        vals = " ".join(str(v) for v in row if str(v) != 'nan')
        if 'S No.' in vals and 'Transaction Date' in vals:
            return i
    return None


def _parse_icici_as_excel(filepath):
    """
    Parse ICICI savings statement from XLS/XLSX.
    Returns a DataFrame with Date, Description, Amount, Type, Source, File columns
    plus a '_balance' column for closing balance extraction.
    """
    try:
        header_row_idx = _find_icici_header_row_excel(filepath)
        if header_row_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Header not found"

        df = pd.read_excel(filepath, header=header_row_idx)
        df.columns = [str(col).strip() for col in df.columns]

        # Find balance column
        balance_col = next(
            (c for c in df.columns if 'balance' in c.lower()),
            None
        )

        return _parse_icici_txn_rows(df, os.path.basename(filepath), balance_col)
    except Exception as e:
        return f"Failed to parse {os.path.basename(filepath)}: {e}"


def _read_icici_csv_as_df(filepath):
    """Read ICICI CSV and return a DataFrame with balance column attached."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        header_row_idx = None
        for i, line in enumerate(lines):
            if 'S No.' in line and 'Transaction Date' in line:
                header_row_idx = i
                break
        if header_row_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Header not found"
        df = pd.read_csv(filepath, skiprows=header_row_idx)
        df.columns = [str(col).strip() for col in df.columns]
        balance_col = next(
            (c for c in df.columns if 'balance' in c.lower()),
            None
        )
        return _parse_icici_txn_rows(df, os.path.basename(filepath), balance_col)
    except Exception as e:
        return f"Failed to parse {os.path.basename(filepath)}: {e}"


def _parse_icici_txn_rows(df, filename, balance_col):
    """
    Common row-parsing logic for both CSV and XLS ICICI savings statements.
    Returns a DataFrame with standard columns + '_balance' for closing balance use.
    """
    rows = []
    for _, row in df.iterrows():
        try:
            s_no = str(row.get('S No.', '')).strip()
            if not s_no or s_no in ['nan', '', 'None']:
                continue

            txn_date = str(row.get('Transaction Date', '')).strip()
            if not txn_date or txn_date in ['nan', '', 'None']:
                continue

            description = str(row.get('Transaction Remarks', '')).strip()
            if description == 'nan':
                description = ''

            withdrawal = 0.0
            deposit = 0.0
            for col in df.columns:
                if 'withdrawal' in col.lower() and 'inr' in col.lower():
                    try:
                        val = row[col]
                        if pd.notna(val) and float(val) > 0:
                            withdrawal = float(val)
                    except Exception:
                        pass
                elif 'deposit' in col.lower() and 'inr' in col.lower():
                    try:
                        val = row[col]
                        if pd.notna(val) and float(val) > 0:
                            deposit = float(val)
                    except Exception:
                        pass

            if withdrawal == 0.0 and deposit == 0.0:
                continue

            amount = withdrawal if withdrawal > 0 else deposit
            typ = "Debit" if withdrawal > 0 else "Credit"

            bal = None
            if balance_col:
                try:
                    bal = float(row[balance_col])
                except Exception:
                    pass

            raw_line = ' | '.join(str(v) for v in row.values if str(v).strip() not in ('', 'nan', 'None', 'NaT'))
            rows.append({
                "Date": pd.to_datetime(txn_date, dayfirst=True, errors='coerce'),
                "Transaction Date": txn_date,
                "Description": description,
                "Amount": amount,
                "Type": typ,
                "Source": "ICICI Savings Account",
                "File": filename,
                "_balance": bal,
                "RawLine": raw_line,
            })
        except Exception:
            continue

    if not rows:
        return f"Failed to parse {filename}: No valid transactions found"

    result_df = pd.DataFrame(rows)
    result_df = result_df[result_df['Date'].notna()]
    if result_df.empty:
        return f"Failed to parse {filename}: No valid dates found"
    return result_df


def parse_icici_csv(filepath):
    """
    Parse ICICI Bank CSV
    
    ICICI CSV format has:
    - Leading empty column
    - Header row with: S No., Value Date, Transaction Date, Cheque Number, 
      Transaction Remarks, Withdrawal Amount (INR ), Deposit Amount (INR ), Balance (INR )
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        DataFrame with columns: Date, Description, Amount, Type, Source, File
        Or error message string if parsing fails
    """
    try:
        # Read the entire file to find header
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the header row (contains "S No." and "Transaction Date")
        header_row_idx = None
        for i, line in enumerate(lines):
            if 'S No.' in line and 'Transaction Date' in line:
                header_row_idx = i
                break
        
        if header_row_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Header not found"
        
        # Read CSV starting from header row
        df = pd.read_csv(filepath, skiprows=header_row_idx)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        rows = []
        for idx, row in df.iterrows():
            try:
                # Check if S No. column has valid data
                if 'S No.' in df.columns:
                    s_no = str(row['S No.']).strip()
                    if not s_no or s_no in ['nan', '', 'None']:
                        continue
                else:
                    # If no S No. column, skip
                    continue
                
                # Get transaction date
                txn_date = None
                if 'Transaction Date' in df.columns:
                    txn_date = str(row['Transaction Date']).strip()
                
                if not txn_date or txn_date in ['nan', '', 'None']:
                    continue
                
                # Get description/remarks
                description = ''
                if 'Transaction Remarks' in df.columns:
                    description = str(row['Transaction Remarks']).strip()
                    if description == 'nan':
                        description = ''
                
                # Get withdrawal and deposit amounts
                # Pandas already parses these as floats, so just use them directly
                withdrawal = 0.0
                deposit = 0.0
                
                for col in df.columns:
                    if 'withdrawal' in col.lower() and 'inr' in col.lower():
                        try:
                            val = row[col]
                            if pd.notna(val) and val > 0:
                                withdrawal = float(val)
                        except:
                            pass
                    elif 'deposit' in col.lower() and 'inr' in col.lower():
                        try:
                            val = row[col]
                            if pd.notna(val) and val > 0:
                                deposit = float(val)
                        except:
                            pass
                
                # Skip if no amount
                if withdrawal == 0.0 and deposit == 0.0:
                    continue
                
                # Determine amount and type
                amount = withdrawal if withdrawal > 0 else deposit
                typ = "Debit" if withdrawal > 0 else "Credit"
                
                rows.append({
                    "Date": pd.to_datetime(txn_date, dayfirst=True, errors='coerce'),
                    "Description": description,
                    "Amount": amount,
                    "Type": typ,
                    "Source": "ICICI Savings Account",
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


def parse_icici_cc_csv(filepath):
    """
    Parse ICICI Credit Card Statement CSV
    
    Format:
    - Header rows with account info
    - "Transaction Details:" line
    - Column headers: Date, Sr.No., Transaction Details, Reward Point Header, Intl.Amount, Amount(in Rs), BillingAmountSign
    - Card number line
    - Transaction rows
    
    BillingAmountSign:
    - Empty string ("") = Debit (money spent on card)
    - "CR" = Credit (payment received/refund)
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        DataFrame with columns: Date, Description, Amount, Type, Source, File
        Or error message string if parsing fails
    """
    try:
        # Read the entire file
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the header row (contains "Date","Sr.No.","Transaction Details")
        header_row_idx = None
        for i, line in enumerate(lines):
            if '"Date"' in line and '"Transaction Details"' in line and '"Amount(in Rs)"' in line:
                header_row_idx = i
                break
        
        if header_row_idx is None:
            return f"Failed to parse {os.path.basename(filepath)}: Credit card header not found"
        
        # Read CSV starting from header row
        # Skip the card number line that comes right after header
        df = pd.read_csv(filepath, skiprows=header_row_idx)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Find card number (it will be in the Date column of first row)
        card_last_4 = None
        if not df.empty and 'Date' in df.columns:
            first_val = str(df.iloc[0]['Date']).strip()
            if 'XXXX' in first_val or len(first_val) > 10:  # Card number format
                card_last_4 = first_val[-4:] if len(first_val) >= 4 else first_val
                df = df.iloc[1:]  # Skip the card number row
        
        rows = []
        for idx, row in df.iterrows():
            try:
                # Get date
                date_str = str(row['Date']).strip()
                if not date_str or date_str in ['nan', '', 'None'] or 'XXXX' in date_str:
                    continue
                
                # Get transaction details
                description = ''
                if 'Transaction Details' in df.columns:
                    description = str(row['Transaction Details']).strip()
                    if description == 'nan':
                        description = ''
                
                if not description:
                    continue
                
                # Get amount
                amount_val = 0.0
                if 'Amount(in Rs)' in df.columns:
                    try:
                        amount_str = str(row['Amount(in Rs)']).strip()
                        if amount_str and amount_str != 'nan':
                            amount_val = float(amount_str.replace(',', ''))
                    except:
                        pass
                
                if amount_val == 0.0:
                    continue
                
                # Determine transaction type based on BillingAmountSign
                # Empty string or missing = Debit (money spent)
                # "CR" = Credit (payment received/refund)
                txn_type = "Debit"
                if 'BillingAmountSign' in df.columns:
                    sign = str(row['BillingAmountSign']).strip().upper()
                    if sign == 'CR':
                        txn_type = "Credit"
                
                raw_line = ' | '.join(str(v) for v in row.values if str(v).strip() not in ('', 'nan', 'None', 'NaT'))
                rows.append({
                    "Date": pd.to_datetime(date_str, dayfirst=True, errors='coerce'),
                    "Description": description,
                    "Amount": amount_val,
                    "Type": txn_type,
                    "Source": f"ICICI Amazon Pay CC (ending {card_last_4})" if card_last_4 else "ICICI Amazon Pay CC",
                    "File": os.path.basename(filepath),
                    "RawLine": raw_line,
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

