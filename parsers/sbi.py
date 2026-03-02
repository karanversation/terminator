"""
SBI Bank Statement Parser
Supports CSV format and password-protected XLSX (netbanking download).
"""

import io
import os
import re
from pathlib import Path
from typing import List, Union

import pandas as pd

from .base import BaseParser, RawTransaction

def _decrypt_sbi_xlsx(filepath: Path) -> io.BytesIO:
    """Decrypt a password-protected SBI XLSX and return a BytesIO buffer."""
    try:
        import msoffcrypto
    except ImportError:
        raise ImportError("msoffcrypto-tool is required for password-protected SBI files. Run: pip install msoffcrypto-tool")
    password = os.environ.get("SBI_XLSX_PASSWORD", "")
    if not password:
        raise ValueError(
            "SBI_XLSX_PASSWORD is not set. Add it to .streamlit/secrets.toml:\n"
            "  SBI_XLSX_PASSWORD = \"your_password\""
        )
    with open(filepath, 'rb') as f:
        office_file = msoffcrypto.OfficeFile(f)
        office_file.load_key(password=password)
        buf = io.BytesIO()
        office_file.decrypt(buf)
    buf.seek(0)
    return buf


def _parse_sbi_xlsx(filepath: Path):
    """
    Parse SBI netbanking XLSX statement (password-protected).

    Format:
      Rows 0-16: account metadata
        Row 3:  'Date of Statement  :  DD-MM-YYYY'
        Row 4:  'Clear Balance  :  X,XX,XXX.XXCR'
      Row 17: header — Date | Details | Ref No/Cheque No | Debit | Credit | Balance
      Rows 18+: transactions (stops at empty rows / summary section)

    Returns DataFrame with Date, Description, Amount, Type, Source, File columns
    plus '_balance' and '_report_date' for closing balance extraction.
    Or returns an error string.
    """
    try:
        buf = _decrypt_sbi_xlsx(filepath)
        raw = pd.read_excel(buf, header=None)

        # Extract statement date and clear balance from metadata rows
        statement_date = None
        clear_balance = None
        for _, row in raw.iterrows():
            cell = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
            m = re.search(r'Date of Statement\s*:\s*(\d{2}-\d{2}-\d{4})', cell)
            if m:
                statement_date = pd.to_datetime(m.group(1), dayfirst=True).date()
            m2 = re.search(r'Clear Balance\s*:\s*([\d,]+\.\d+)CR', cell)
            if m2:
                clear_balance = float(m2.group(1).replace(',', ''))

        # Find header row (contains 'Date' and 'Balance' and 'Details')
        header_row_idx = None
        for i, row in raw.iterrows():
            vals = [str(v) for v in row if str(v) != 'nan']
            if 'Date' in vals and 'Balance' in vals and 'Details' in vals:
                header_row_idx = i
                break

        if header_row_idx is None:
            return f"Failed to parse {filepath.name}: transaction header not found"

        buf.seek(0)
        df = pd.read_excel(buf, header=header_row_idx)
        df.columns = [str(c).strip() for c in df.columns]

        date_col = next((c for c in df.columns if c.lower() == 'date'), None)
        desc_col = next((c for c in df.columns if 'detail' in c.lower()), None)
        debit_col = next((c for c in df.columns if 'debit' in c.lower()), None)
        credit_col = next((c for c in df.columns if 'credit' in c.lower()), None)
        balance_col = next((c for c in df.columns if 'balance' in c.lower()), None)

        if not date_col:
            return f"Failed to parse {filepath.name}: Date column not found"

        rows = []
        for _, row in df.iterrows():
            try:
                date_val = row[date_col]
                # Stop at summary/footer rows (date cell is not a real date)
                if pd.isna(date_val):
                    continue
                date_str = str(date_val).strip()
                if not date_str or date_str in ('nan', ''):
                    continue
                parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                if pd.isna(parsed_date):
                    continue

                description = ''
                if desc_col:
                    description = str(row[desc_col]).strip().replace('\n', ' ')
                    if description == 'nan':
                        description = ''

                debit = 0.0
                credit = 0.0
                if debit_col and pd.notna(row[debit_col]):
                    try:
                        debit = float(str(row[debit_col]).replace(',', ''))
                    except Exception:
                        pass
                if credit_col and pd.notna(row[credit_col]):
                    try:
                        credit = float(str(row[credit_col]).replace(',', ''))
                    except Exception:
                        pass

                if debit == 0.0 and credit == 0.0:
                    continue

                bal = None
                if balance_col and pd.notna(row[balance_col]):
                    try:
                        bal = float(str(row[balance_col]).replace(',', ''))
                    except Exception:
                        pass

                raw_line = ' | '.join(str(v) for v in row.values if str(v).strip() not in ('', 'nan', 'None', 'NaT'))
                rows.append({
                    "Date": parsed_date,
                    "Description": description,
                    "Amount": debit if debit > 0 else credit,
                    "Type": "Debit" if debit > 0 else "Credit",
                    "Source": "SBI Account",
                    "File": filepath.name,
                    "_balance": bal,
                    "_report_date": statement_date,
                    "RawLine": raw_line,
                })
            except Exception:
                continue

        if not rows:
            return f"Failed to parse {filepath.name}: No valid transactions found"

        result_df = pd.DataFrame(rows)
        result_df = result_df[result_df['Date'].notna()]
        # Attach statement-level closing balance for use by get_closing_balance()
        result_df['_clear_balance'] = clear_balance
        result_df['_statement_date'] = statement_date
        return result_df

    except Exception as e:
        return f"Failed to parse {filepath.name}: {e}"


# ---------------------------------------------------------------------------
# Parser class (new architecture)
# ---------------------------------------------------------------------------

class SbiSavingsParser(BaseParser):
    account = "SBI Account"
    account_type = "savings"

    def parse(self, filepath: Path) -> "Union[List[RawTransaction], str]":
        suffix = filepath.suffix.lower()
        if suffix in ('.xlsx', '.xls'):
            df = _parse_sbi_xlsx(filepath)
        else:
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
                raw_line=str(row.get("RawLine", "")),
            ))
        return rows

    def get_closing_balance(self, filepath: Path):
        """Return (report_date, closing_balance)."""
        suffix = filepath.suffix.lower()
        if suffix in ('.xlsx', '.xls'):
            df = _parse_sbi_xlsx(filepath)
            if isinstance(df, str):
                raise ValueError(df)
            # Prefer the statement-level date + clear balance for accuracy
            stmt_date = df['_statement_date'].iloc[0]
            clear_bal = df['_clear_balance'].iloc[0]
            if stmt_date and clear_bal is not None:
                return stmt_date, clear_bal
            # Fallback: last transaction row
            for _, row in df[::-1].iterrows():
                if pd.notna(row.get('_balance')) and pd.notna(row['Date']):
                    return row['Date'].date(), float(row['_balance'])
            raise ValueError(f"Could not extract closing balance from {filepath.name}")

        # CSV path
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        header_row_idx = None
        for i, line in enumerate(lines):
            if 'Txn Date' in line:
                header_row_idx = i
                break

        if header_row_idx is None:
            raise ValueError(f"SBI header not found in {filepath.name}")

        df = pd.read_csv(filepath, skiprows=header_row_idx, on_bad_lines='skip', header=0)
        df.columns = [str(col).strip() for col in df.columns]

        date_col = None
        balance_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'txn date' in col_lower:
                date_col = col
            elif 'balance' in col_lower:
                balance_col = col

        if not date_col or not balance_col:
            raise ValueError(f"Required columns not found in {filepath.name}")

        for _, row in df[::-1].iterrows():
            try:
                date_str = str(row[date_col]).strip()
                if not date_str or date_str in ['nan', '', 'None', 'Txn Date']:
                    continue
                bal_str = str(row[balance_col]).strip().replace(',', '').replace('"', '')
                if not bal_str or bal_str in ['nan', '', 'None']:
                    continue
                parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                if pd.isna(parsed_date):
                    continue
                return parsed_date.date(), float(bal_str)
            except Exception:
                continue

        raise ValueError(f"Could not extract closing balance from {filepath.name}")


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
                
                raw_line = ' | '.join(str(v) for v in row.values if str(v).strip() not in ('', 'nan', 'None', 'NaT'))
                rows.append({
                    "Date": pd.to_datetime(txn_date, dayfirst=True, errors='coerce'),
                    "Description": description,
                    "Amount": amount,
                    "Type": typ,
                    "Source": "SBI Account",
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

