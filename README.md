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

1. Place your transaction files in the `source_files/` directory:
   - HDFC Credit Card statements (CSV format with `Billedstatements` in filename)
   - Bank statements (TXT, XLS, or CSV formats)

2. Run the Streamlit app:
```bash
streamlit run main.py
```

3. Open your browser (usually auto-opens) to view the dashboard

4. Use the sidebar filters to:
   - Select date ranges
   - Filter by transaction type (Debit/Credit)
   - Choose specific categories
   - Select payment methods
   - Set amount ranges

5. Explore different tabs:
   - **Overview**: Get a high-level summary with key metrics and charts
   - **Monthly Analysis**: View month-by-month trends and breakdowns
   - **Annual Analysis**: Compare yearly expenses and quarterly patterns
   - **Category Analysis**: Deep dive into spending by category
   - **Transaction Details**: Search and browse individual transactions

## File Format Support

### HDFC Credit Card Statements
- Format: CSV with `~` delimiter
- Filename pattern: `*Billedstatements*.csv`
- Distinguishes between Diners Black (2508) and Regalia (6598)

### HDFC Savings Account
- Format: TXT with fixed-width columns
- Filename pattern: `Acct_Statement*.txt`

### ICICI Bank Statements
- Format: XLS
- Filename pattern: `OpTransactionHistory*.xls`

### SBI Bank Statements
- Format: CSV exported from XLS
- Filename pattern: `SBI*.csv`

### ICICI Bank Statements
- Format: CSV exported from XLS
- Filename pattern: `ICICI*.csv`
- Note: If CSV export doesn't work properly, the ICICI statement can be manually imported or the parser can be adjusted based on your specific format

## Customization

### Adding New Categories
Edit the `CATEGORY_RULES` dictionary in `main.py`:

```python
CATEGORY_RULES = {
    'Your Category': [
        'keyword1', 'keyword2', 'keyword3'
    ],
    # ... other categories
}
```

### Adding New Payment Methods
Modify the `identify_payment_method()` function in `main.py` to recognize additional payment sources.

## Data Privacy

- All data processing happens locally on your machine
- No data is sent to external servers
- Your transaction files remain in your local `source_files/` directory

## Tips

1. **Regular Updates**: Add new statements regularly to keep your analysis up-to-date
2. **Multiple Years**: Include multiple years of data for better trend analysis
3. **Export Data**: Use the CSV export feature to create backups or further analysis in Excel
4. **Search Function**: Use the transaction search to quickly find specific expenses
5. **Category Refinement**: Update category keywords based on your spending patterns

## Troubleshooting

### If transactions aren't loading:
- Check file formats match supported types
- Ensure files are in the `source_files/` directory
- Check the error messages in the expandable warning section

### If categories seem wrong:
- Update the `CATEGORY_RULES` dictionary with more specific keywords
- Keywords are matched case-insensitively

### If the app is slow:
- Consider filtering by date range to reduce data volume
- Limit the number of files in `source_files/` to recent months only

## Requirements

- Python 3.9+
- streamlit
- pandas
- plotly
- openpyxl
- xlrd

## License

Personal use only. Keep your financial data secure.

