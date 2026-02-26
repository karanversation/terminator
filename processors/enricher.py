"""
Transaction Data Enrichment
Adds derived columns to transaction data
"""

from .categorizer import categorize_transaction, identify_payment_method


def enrich_transactions(df):
    """
    Add derived columns to transactions dataframe
    
    Args:
        df: DataFrame with basic transaction data
        
    Returns:
        DataFrame with additional columns:
        - Category: Transaction category
        - Payment Method: Payment method used
        - Year: Transaction year
        - Month: Transaction month number
        - Month-Year: YYYY-MM format
        - Quarter: Quarter number
        
    Note: Credit card payments from bank accounts are reclassified as 'Transfer' 
          to avoid double counting (the actual expenses are in credit card statements)
    """
    # Add category based on transaction type
    df['Category'] = df.apply(
        lambda x: categorize_transaction(x['Description'], x['Type']), 
        axis=1
    )
    
    # Add payment method
    df['Payment Method'] = df.apply(
        lambda x: identify_payment_method(x['Source'], x['Description'], x['File']), 
        axis=1
    )
    
    # Add date-based columns
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['Month-Year'] = df['Date'].dt.strftime('%Y-%m')
    df['Quarter'] = df['Date'].dt.quarter
    
    # IMPORTANT: Prevent double counting of credit card expenses
    # When you pay your credit card bill from your bank account, that payment should NOT
    # be counted as an expense because the actual expenses were already counted when you
    # made purchases on the credit card (those are in the credit card statement files).
    # 
    # Example:
    #   1. You spend Rs. 10,000 on dining using credit card -> Counted as expense (from CC statement)
    #   2. You pay Rs. 10,000 credit card bill from bank -> Should NOT be counted again
    #
    # Solution: Reclassify credit card payments from bank accounts as 'Transfer' (not 'Debit')
    # Use account_type if available (new DB path), else fall back to Source name list
    if 'account_type' in df.columns:
        cc_payment_mask = (
            (df['Category'] == 'Credit Card Payment') &
            (df['account_type'] == 'savings') &
            (df['Type'] == 'Debit')
        )
    else:
        bank_sources = ['HDFC Savings Account', 'ICICI Savings Account', 'SBI Account']
        cc_payment_mask = (
            (df['Category'] == 'Credit Card Payment') &
            (df['Source'].isin(bank_sources)) &
            (df['Type'] == 'Debit')
        )
    df.loc[cc_payment_mask, 'Type'] = 'Transfer'
    
    # Sort by date
    df = df.sort_values('Date', ascending=False)
    
    return df

