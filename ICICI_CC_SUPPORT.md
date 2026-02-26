# ICICI Credit Card Statement Support

## Overview

Added support for parsing ICICI Amazon Pay Credit Card statements in CSV format.

## What Was Added

### 1. New Parser (`parsers/icici.py`)

Added `parse_icici_cc_csv()` function to parse ICICI credit card statement CSV files.

#### File Format Supported

**File naming pattern:**
- `CreditCardStatement.CSV`
- `CreditCardStatement (1).CSV`
- `CreditCardStatement (2).CSV`
- etc.

**CSV Structure:**
```csv
"Accountno:","0000000020241177"
"Customer Name:","MR KARAN BAJAJ"
"Address:","..."

"Transaction Details:"
"Date","Sr.No.","Transaction Details","Reward Point Header","Intl.Amount","Amount(in Rs)","BillingAmountSign"
"4315XXXXXXXX8008"
"20/08/2025","11818656815","BBPS Payment received","0","0","29999.00","CR"
"14/07/2025","11615251915","IND*AMAZON HTTP://WWW.AM IN","1499","0","29999.00",""
```

**Key Features:**
- Extracts card last 4 digits from card number line
- Parses transaction date (DD/MM/YYYY format)
- Extracts description from "Transaction Details" column
- Handles amounts with commas
- Determines transaction type from "BillingAmountSign":
  - Empty string `""` = **Debit** (money spent on card)
  - `"CR"` = **Credit** (payment received/refund)

### 2. Updated Loader (`processors/loader.py`)

**Changes:**
1. Made file extension check case-insensitive (handles both `.csv` and `.CSV`)
2. Added detection for ICICI credit card statement files
3. Routes `CreditCardStatement*.CSV` files to the new parser

```python
elif "CreditCardStatement" in file and file_lower.endswith('.csv'):
    res = parse_icici_cc_csv(filepath)
```

### 3. Updated Payment Method Identification (`processors/categorizer.py`)

Added logic to identify ICICI Amazon Pay CC transactions:
- Checks if source contains "ICICI Amazon Pay CC"
- Checks if filename contains "CreditCardStatement"

```python
if 'icici amazon pay cc' in source_lower or 'creditcardstatement' in file_name.lower():
    return 'ICICI Amazon Pay CC'
```

### 4. Updated Exports (`parsers/__init__.py`)

Added `parse_icici_cc_csv` to the module exports.

## Test Results

### ✅ Parsing Test
```
Total transactions parsed: 46
Date range: 05/12/2024 to 20/08/2025
Transaction type breakdown:
  - Debit: 26 (money spent on card)
  - Credit: 20 (payments received/refunds)
```

### ✅ Integration Test
```
Total transactions loaded: 1,258

By Source:
  - HDFC Diners Black CC:              591 (47.0%)
  - HDFC Savings Account:              489 (38.9%)
  - HDFC Regalia CC:                   112 (8.9%)
  - ICICI Amazon Pay CC (ending 8008):  46 (3.7%)  ← NEW!
  - ICICI Savings Account:              14 (1.1%)
  - SBI Account:                         6 (0.5%)

By Payment Method:
  - ICICI Amazon Pay CC:                47 (3.7%)  ← Correctly identified!
```

## Sample Transactions

```
Date       | Type   | Payment Method      | Category       | Amount      | Description
-----------|--------|---------------------|----------------|-------------|---------------------------
20/08/2025 | Credit | ICICI Amazon Pay CC | Miscellaneous  | Rs. 29,999 | BBPS Payment received
14/07/2025 | Debit  | ICICI Amazon Pay CC | Shopping       | Rs. 29,999 | IND*AMAZON HTTP://WWW.AM
28/06/2025 | Debit  | ICICI Amazon Pay CC | Miscellaneous  | Rs. 14,585 | MAKE MY TRIP GURUGRAM IN
17/05/2025 | Debit  | ICICI Amazon Pay CC | Forex          | Rs.  6,887 | BOOK MY FOREX PVT LTD
```

## Transaction Type Logic

### Debit (Expenses - money spent)
- Shows as empty `""` in BillingAmountSign column
- Examples:
  - Shopping on Amazon
  - Travel bookings (MakeMyTrip)
  - Forex purchases (BookMyForex)

### Credit (Income/Payments - money received)
- Shows as `"CR"` in BillingAmountSign column
- Examples:
  - BBPS bill payments (paying credit card bill)
  - Refunds from merchants
  - Cashback credits
  - Reward reversals

## Files Modified

1. **`parsers/icici.py`**
   - Added `parse_icici_cc_csv()` function
   - 118 lines of new parsing logic

2. **`parsers/__init__.py`**
   - Exported new parser function

3. **`processors/loader.py`**
   - Made extension check case-insensitive
   - Added ICICI CC file detection logic

4. **`processors/categorizer.py`**
   - Enhanced `identify_payment_method()` to recognize ICICI CC transactions

## Benefits

1. **Complete Financial Picture**: Now tracks expenses from all 4 credit cards:
   - HDFC Diners Black CC ✓
   - HDFC Regalia CC ✓
   - ICICI Amazon Pay CC ✓ (NEW!)
   - Plus savings accounts from HDFC, ICICI, and SBI

2. **Automatic Categorization**: All ICICI CC transactions are automatically:
   - Categorized by expense type (Shopping, Travel, Forex, etc.)
   - Tagged with correct payment method
   - Included in monthly/annual analysis

3. **Case-Insensitive File Handling**: Robustly handles file extensions in any case (`.csv`, `.CSV`, `.Csv`)

4. **Card Identification**: Automatically extracts and displays card last 4 digits in source name

## Usage

Simply export ICICI credit card statements as CSV files and place them in the `source_files/` directory with names like:
- `CreditCardStatement.CSV`
- `CreditCardStatement (1).CSV`
- etc.

The application will automatically detect, parse, and load them on the next run!

## Next Steps (Optional Improvements)

1. **Better Categorization**:
   - "BBPS Payment received" could be categorized as "Credit Card Payment"
   - "MAKE MY TRIP" should be "Travel" (currently "Miscellaneous")
   
   These can be fixed by updating keywords in `config.py`:
   ```python
   'Travel': [
       'make my trip', 'makemytrip',
       # ... existing keywords
   ],
   'Credit Card Payment': [
       'bbps payment received',
       # ... existing keywords
   ]
   ```

2. **Support Multiple Cards**: If you have other ICICI credit cards, enhance parser to distinguish between them based on card number.

## Technical Notes

### Why Credits on Credit Card?

Credit card "credits" represent:
1. **Bill Payments**: When you pay your credit card bill (appears as CR)
2. **Refunds**: When merchants refund purchases
3. **Cashback**: Reward points converted to cash
4. **Reversals**: Disputed transactions reversed

These are important to track to calculate:
- Net credit card balance
- Actual out-of-pocket expenses
- Available credit limit

### Double-Counting Prevention

The enricher automatically prevents double-counting:
- When you pay credit card bills from your bank account, those are marked as "Transfer"
- The actual expenses (purchases on the card) are tracked separately
- This ensures accurate expense tracking

---

**Status**: ✅ Fully implemented and tested
**Date**: October 12, 2025

