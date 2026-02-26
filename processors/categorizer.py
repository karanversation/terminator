"""
Transaction Categorization and Payment Method Identification
Supports both simple string matching and regex patterns
"""

import pandas as pd
import re
from config import EXPENSE_CATEGORY_RULES, INCOME_CATEGORY_RULES


def categorize_transaction(description, transaction_type='Debit'):
    """
    Categorize a transaction based on its description and type
    Supports both plain string keywords and regex patterns
    
    Regex patterns should be specified as raw strings starting with 'r:' prefix
    Example: 'r:si hga[ifp]p' will match 'SI HGAIP', 'SI HGAFP', 'SI HGAGP'
    
    Args:
        description: Transaction description string
        transaction_type: 'Debit' for expenses or 'Credit' for income
        
    Returns:
        Category name (string)
    """
    if pd.isna(description):
        return 'Miscellaneous'
    
    desc_lower = str(description).lower()
    
    # Select appropriate category rules based on transaction type
    category_rules = INCOME_CATEGORY_RULES if transaction_type == 'Credit' else EXPENSE_CATEGORY_RULES
    
    # Score-based matching: longer/more specific patterns get higher scores
    category_scores = {}
    
    for category, keywords in category_rules.items():
        if category == 'Miscellaneous':
            continue  # Skip the default category
        
        score = 0
        matched_keywords = []
        
        for keyword in keywords:
            keyword_str = str(keyword).strip()
            
            # Skip empty keywords
            if not keyword_str:
                continue
            
            # Check if this is a regex pattern (starts with 'r:')
            is_regex = keyword_str.startswith('r:')
            
            if is_regex:
                # Extract regex pattern (remove 'r:' prefix)
                pattern = keyword_str[2:].lower()
                try:
                    # Try to match the regex pattern
                    match = re.search(pattern, desc_lower)
                    if match:
                        # Score based on matched text length
                        matched_text = match.group(0)
                        keyword_score = len(matched_text)
                        
                        # Bonus for matches at start
                        if match.start() == 0:
                            keyword_score *= 1.5
                        
                        # Bonus for longer patterns (more specific)
                        keyword_score *= (1 + len(pattern) / 20)
                        
                        score += keyword_score
                        matched_keywords.append(f'regex:{pattern}')
                except re.error:
                    # Invalid regex, skip it
                    continue
            else:
                # Plain string matching (original logic)
                keyword_lower = keyword_str.lower()
                
                if keyword_lower in desc_lower:
                    # Score based on keyword specificity
                    keyword_score = len(keyword_lower)
                    
                    # Bonus for multi-word phrases (more specific)
                    if ' ' in keyword_lower:
                        keyword_score *= 3
                    
                    # Bonus for matches at start (more relevant)
                    if desc_lower.startswith(keyword_lower):
                        keyword_score *= 1.5
                    
                    score += keyword_score
                    matched_keywords.append(keyword_lower)
        
        if score > 0:
            category_scores[category] = {
                'score': score,
                'keywords': matched_keywords
            }
    
    # Return category with highest score
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
        return best_category[0]
    
    return 'Miscellaneous'


def get_categorization_details(description, transaction_type='Debit'):
    """
    Get detailed categorization information for debugging purposes
    Supports both plain string keywords and regex patterns
    
    Args:
        description: Transaction description string
        transaction_type: 'Debit' for expenses or 'Credit' for income
        
    Returns:
        Dictionary with category, score, and matched keywords
    """
    if pd.isna(description):
        return {'category': 'Miscellaneous', 'score': 0, 'keywords': [], 'all_matches': {}}
    
    desc_lower = str(description).lower()
    
    # Select appropriate category rules based on transaction type
    category_rules = INCOME_CATEGORY_RULES if transaction_type == 'Credit' else EXPENSE_CATEGORY_RULES
    
    # Score-based matching
    category_scores = {}
    
    for category, keywords in category_rules.items():
        if category == 'Miscellaneous':
            continue
        
        score = 0
        matched_keywords = []
        
        for keyword in keywords:
            keyword_str = str(keyword).strip()
            if not keyword_str:
                continue
            
            # Check if this is a regex pattern (starts with 'r:')
            is_regex = keyword_str.startswith('r:')
            
            if is_regex:
                # Extract regex pattern (remove 'r:' prefix)
                pattern = keyword_str[2:].lower()
                try:
                    match = re.search(pattern, desc_lower)
                    if match:
                        matched_text = match.group(0)
                        keyword_score = len(matched_text)
                        if match.start() == 0:
                            keyword_score *= 1.5
                        keyword_score *= (1 + len(pattern) / 20)
                        score += keyword_score
                        matched_keywords.append(f'regex:{pattern}')
                except re.error:
                    continue
            else:
                # Plain string matching
                keyword_lower = keyword_str.lower()
                if keyword_lower in desc_lower:
                    keyword_score = len(keyword_lower)
                    if ' ' in keyword_lower:
                        keyword_score *= 3
                    if desc_lower.startswith(keyword_lower):
                        keyword_score *= 1.5
                    score += keyword_score
                    matched_keywords.append(keyword_lower)
        
        if score > 0:
            category_scores[category] = {
                'score': score,
                'keywords': matched_keywords
            }
    
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
        return {
            'category': best_category[0],
            'score': best_category[1]['score'],
            'keywords': best_category[1]['keywords'],
            'all_matches': category_scores
        }
    
    return {'category': 'Miscellaneous', 'score': 0, 'keywords': [], 'all_matches': {}}


def identify_payment_method(source, description, file_name):
    """
    Identify the payment method used for a transaction
    
    Args:
        source: Transaction source (e.g., "HDFC Savings Account")
        description: Transaction description
        file_name: Source file name
        
    Returns:
        Payment method name (string)
    """
    desc_lower = str(description).lower() if not pd.isna(description) else ""
    source_lower = str(source).lower() if not pd.isna(source) else ""

    # Credit Cards — use account name (source) since file_name may not be available
    if 'diners' in source_lower or '2508' in file_name:
        return 'HDFC Diners Black CC'
    if 'regalia' in source_lower or '6598' in file_name:
        return 'HDFC Regalia CC'
    if 'icici amazon pay' in source_lower or 'creditcardstatement' in file_name.lower():
        return 'ICICI Amazon Pay CC'
    
    # UPI
    if 'upi-' in desc_lower or 'upi ' in desc_lower:
        return 'UPI'
    
    # ATM
    if 'nwd-' in desc_lower or 'atm' in desc_lower or 'cash withdrawal' in desc_lower:
        return 'ATM Withdrawal'
    
    # Direct transfers
    if any(x in desc_lower for x in ['neft', 'imps', 'rtgs']):
        return 'Direct Transfer'
    
    # Debit cards
    if 'debit card' in desc_lower:
        if 'hdfc' in source.lower():
            return 'HDFC Debit Card'
        elif 'icici' in source.lower():
            return 'ICICI Debit Card'
        elif 'sbi' in source.lower():
            return 'SBI Debit Card'
        else:
            return 'Debit Card'
    
    # Cheque
    if 'chq' in desc_lower or 'cheque' in desc_lower or 'clearing' in desc_lower:
        return 'Cheque'
    
    return 'Other'

