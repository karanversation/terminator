# 💰 Terminator: Transaction Analyzer

A comprehensive expense analysis tool that parses and categorizes transactions from multiple payment sources including credit cards, bank accounts, and UPI payments.

## Features

- **Multi-Source Parsing**: Automatically parses transactions from:
  - HDFC Credit Cards (Diners Black & Regalia)
  - HDFC Savings Account
  - ICICI Bank Account
  - SBI Bank Account
  - And more...

- **Intelligent Categorization**: Automatically categorizes expenses into:
  - Food & Dining
  - Transportation
  - Shopping
  - Utilities & Bills
  - Rent
  - Healthcare
  - Travel
  - Investments
  - Credit Card Payments
  - ATM Withdrawals
  - Transfers
  - Entertainment
  - Miscellaneous

- **Payment Method Tracking**: Identifies and tracks spending across:
  - HDFC Diners Black Credit Card
  - HDFC Regalia Credit Card
  - ICICI Amazon Pay Credit Card
  - UPI Payments
  - ATM Withdrawals
  - Direct Transfers (NEFT/IMPS/RTGS)
  - Debit Cards
  - Cheques
  - Cash

- **Comprehensive Analysis**:
  - Monthly expense trends
  - Annual comparisons
  - Category-wise breakdown
  - Payment method analysis
  - Quarterly summaries
  - Top expenses tracking

- **Interactive Dashboard**:
  - Beautiful visualizations with Plotly
  - Advanced filtering options
  - Search functionality
  - Export to CSV

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Create the `source_files/` directory and **organize statements in subfolders** by source:
   - `source_files/hdfc_cc/` — HDFC Credit Card statements (CSV)
   - `source_files/hdfc_savings/` — HDFC Savings Account (TXT)
   - `source_files/icici_cc/` — ICICI Credit Card (CSV)
   - `source_files/icici_savings/` — ICICI Savings (CSV or TXT)
   - `source_files/sbi/` — SBI statements (CSV)

   Only `.csv` and `.txt` files inside these folders are loaded.

2. Run the Streamlit app:
```bash
streamlit run Home.py
```

3. Open your browser (usually auto-opens) to view the dashboard.

4. Use the sidebar filters to:
   - Select date ranges
   - Filter by transaction type (Debit/Credit)
   - Choose specific categories
   - Select payment methods
   - Set amount ranges

5. Explore the pages via the sidebar:
   - **Home**: Summary metrics and source files browser
   - **Overview**: High-level summary with key metrics and charts
   - **Monthly**: Month-by-month trends and breakdowns
   - **Categories**: Spending by category
   - **Transactions**: Search and browse individual transactions
   - **Review**: Review and adjust categorizations

## File Format Support

Statements must be placed in the correct subfolder under `source_files/` (see Usage). Supported formats:

### File naming

- **No strict filename rule**: Any file with extension `.csv` or `.txt` inside the right subfolder is loaded. You can name files however you like (e.g. `jan2024.csv`, `statement.csv`).
- **HDFC Credit Card (two cards)**: If you have both Diners Black and Regalia, the app identifies the card by the **filename**: include `2508` somewhere in the filename for Diners Black (e.g. `HDFC_Billedstatements_2508_Jan24.csv`). Files without `2508` are treated as Regalia.
- **Conventions** (optional; your bank may use similar names):
  - HDFC CC: often `*Billedstatements*.csv`
  - HDFC Savings: often `Acct_Statement*.txt`
  - ICICI: often `OpTransactionHistory*.csv` or `ICICI*.csv` after export
  - SBI: often `SBI*.csv` after export

### HDFC Credit Card (`source_files/hdfc_cc/`)
- Format: CSV with `~` delimiter
- Diners Black vs Regalia: include `2508` in the filename for Diners Black (see File naming above).

### HDFC Savings (`source_files/hdfc_savings/`)
- Format: TXT with fixed-width columns
- Filename pattern: `Acct_Statement*.txt`

### ICICI Credit Card (`source_files/icici_cc/`)
- Format: CSV
- Place exported ICICI credit card statement CSVs in this folder.

### ICICI Savings (`source_files/icici_savings/`)
- Format: CSV or TXT (e.g. exported from XLS)
- Filename pattern: `OpTransactionHistory*.xls` exported to CSV, or `ICICI*.csv`

### SBI (`source_files/sbi/`)
- Format: CSV (e.g. exported from XLS)
- Filename pattern: `SBI*.csv`

## Customization

### Adding New Categories
Edit the category rules in `config.py`:
- **Expenses**: `EXPENSE_CATEGORY_RULES`
- **Income**: `INCOME_CATEGORY_RULES`

Keywords are matched case-insensitively; patterns starting with `r:` are treated as regex. Optionally, you can maintain `categories.yaml` and ensure the app loads from it if that flow is enabled.

```python
EXPENSE_CATEGORY_RULES = {
    'Your Category': [
        'keyword1', 'keyword2',
        'r:regex_pattern',  # optional regex
    ],
    # ...
}
```

### Adding New Payment Methods
Modify the `identify_payment_method()` function in `processors/categorizer.py` to recognize additional payment sources.

### LLM-assisted categorization (optional)
The Review page can use OpenAI to suggest categories for uncategorized or Miscellaneous transactions. Set your API key in the environment before running the app:

```bash
export OPENAI_API_KEY='your-openai-api-key'
streamlit run Home.py
```

If `OPENAI_API_KEY` is not set, the app falls back to rule-based categorization only.

## Data Privacy

- All data processing happens locally on your machine
- Transaction data is stored in a local SQLite database
- Your source statement files remain in your local `source_files/` directory
- **LLM categorization**: If you set `OPENAI_API_KEY`, transaction descriptions are sent to OpenAI’s API to suggest categories; otherwise no data is sent to external servers

## Tips

1. **Regular Updates**: Add new statements regularly to keep your analysis up-to-date
2. **Multiple Years**: Include multiple years of data for better trend analysis
3. **Export Data**: Use the CSV export feature to create backups or further analysis in Excel
4. **Search Function**: Use the transaction search to quickly find specific expenses
5. **Category Refinement**: Update category keywords based on your spending patterns

## Troubleshooting

### If transactions aren't loading:
- Ensure files are in the correct **subfolder** under `source_files/` (e.g. `hdfc_cc`, `icici_savings`)
- Only `.csv` and `.txt` files are loaded
- Check that file formats match the supported types for that folder
- Check the expandable warning section in the app for parser errors

### If categories seem wrong:
- Update `EXPENSE_CATEGORY_RULES` or `INCOME_CATEGORY_RULES` in `config.py` with more specific keywords
- Keywords are matched case-insensitively; use `r:regex` for pattern-based rules

### If the app is slow:
- Consider filtering by date range to reduce data volume
- Limit the number of files in `source_files/` to recent months only

## Requirements

- Python 3.9+
- streamlit
- pandas
- plotly
- openpyxl
- xlrd==2.0.1
- pyyaml
- openai (optional, for LLM-assisted categorization)

## License

Personal use only. Keep your financial data secure.

