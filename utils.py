"""
Utility functions for Transaction Analyzer
"""

import pandas as pd


def format_inr(amount):
    """
    Format amount in Indian numbering system (lakhs, crores)
    
    Args:
        amount: Numerical amount to format
        
    Returns:
        Formatted string in Indian numbering with rupee symbol (₹1,23,456.00)
    """
    if pd.isna(amount):
        return "₹0"
    
    # Handle negative numbers
    is_negative = amount < 0
    amount = abs(amount)
    
    # Convert to string and split into integer and decimal parts
    amount_str = f"{amount:.2f}"
    parts = amount_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    
    # Indian numbering system: groups of 3 from right, then groups of 2
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        # Last 3 digits
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        
        # Group remaining digits in pairs from right to left
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        
        # Reverse and join
        groups.reverse()
        formatted = ','.join(groups) + ',' + last_three
    
    result = f"₹{formatted}.{decimal_part}"
    return f"-{result}" if is_negative else result

