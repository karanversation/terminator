"""
Merchant name normalizer.
Applies ordered regex rules to clean up raw bank descriptions into human-readable
merchant names. Falls back to title-casing the cleaned string if no rule matches.
"""

import re

# Each rule is (pattern, replacement).
# replacement can be a string or None (meaning "remove the matched part").
# Rules are applied in order; first full-description match wins for named merchants.
# Cleaning rules (prefix/suffix strippers) run first on every description.
_CLEAN_RULES = [
    # Strip UPI prefix variations
    (r'(?i)^upi[-/\s]+', ''),
    # Strip @bank suffix (e.g. @okicici, @ybl, @sbi)
    (r'@\w+$', ''),
    # Strip *SUFFIX (e.g. *HDFC, *SBI)
    (r'\*\w+$', ''),
    # Strip trailing transaction ref numbers (6+ digits)
    (r'\s+\d{6,}.*$', ''),
    # NEFT/IMPS/RTGS full patterns: run BEFORE generic suffix stripping
    # e.g. "IMPS-506721103532-ABHILASHA SINGH" → "Abhilasha Singh"
    # e.g. "NEFT DR-BANKCODE-NAME" → "NAME"
    (r'(?i)^(neft|rtgs)\s*(dr|cr)?[-\s/]+[\w\d][-\w\d]*[-/\s]+', ''),
    (r'(?i)^imps[-/\s]*\d*[-/\s]*', ''),
    # Strip leftover IMPS/NEFT/RTGS prefix after above rules
    (r'(?i)^(imps|neft|rtgs)\s*$', ''),
    # Strip leading bank code patterns like "DR-ICIC0000192-" or "CR-HDFC0000001-"
    (r'(?i)^(dr|cr)[-/\s]+[\w\d]+[-/\s]+', ''),
    # IMPS long ref pattern: remove "-NNNNNNNNNN-..." suffix
    (r'-\d{8,}-.*$', ''),
    # Strip leading/trailing whitespace (run last in clean rules)
    (r'^\s+|\s+$', ''),
]

_MERCHANT_RULES: list[tuple[str, str]] = [
    # ATM / Cash
    (r'(?i)nwd[-\s].*|atw[-\s].*|cash\s*withdrawal.*|atm\s*with.*|cash\s*wdl.*', 'ATM Withdrawal'),
    # Food delivery & parent companies
    (r'(?i)zomato', 'Zomato'),
    (r'(?i)eternal\s*(limited|ltd)?', 'Eternal (Zomato/Blinkit)'),  # Zomato parent since Jan 2025
    (r'(?i)swiggy', 'Swiggy'),
    (r'(?i)blinkit', 'Blinkit'),
    (r'(?i)zepto', 'Zepto'),
    (r'(?i)bigbasket', 'BigBasket'),
    (r'(?i)dunzo', 'Dunzo'),
    # Grocery
    (r'(?i)avenue\s*supermarts', 'DMart (Avenue Supermarts)'),
    # Restaurants
    (r'(?i)truffles\s*hospitality', 'Truffles Hospitality'),
    (r'(?i)blue\s*tokai', 'Blue Tokai'),
    (r'(?i)bikanervala', 'Bikanervala'),
    (r'(?i)costa\s*coffee|costa\s*dt', 'Costa Coffee'),
    (r'(?i)mcdonald', "McDonald's"),
    (r'(?i)domino', "Domino's"),
    (r'(?i)starbucks', 'Starbucks'),
    (r'(?i)kfc', 'KFC'),
    (r'(?i)carnatic\s*cafe', 'Carnatic Cafe'),
    # Grocery
    (r'(?i)jiomart', 'JioMart'),
    (r'(?i)dmart|d[\s-]?mart', 'DMart'),
    (r'(?i)reliance\s*(fresh|smart)', 'Reliance Retail'),
    # E-commerce
    (r'(?i)amazon(?!\s*pay)', 'Amazon'),
    (r'(?i)amazon\s*pay', 'Amazon Pay'),
    (r'(?i)flipkart', 'Flipkart'),
    (r'(?i)myntra', 'Myntra'),
    (r'(?i)ajio', 'AJIO'),
    (r'(?i)meesho', 'Meesho'),
    (r'(?i)nykaa', 'Nykaa'),
    # Ride / Transport
    (r'(?i)ubertrip|uber\s*trip', 'Uber'),
    (r'(?i)uber', 'Uber'),
    (r'(?i)olacabs|ola\s*cabs', 'Ola'),
    (r'(?i)rapido', 'Rapido'),
    (r'(?i)blu\s*smart', 'BluSmart'),
    (r'(?i)fastag', 'FASTag'),
    # Streaming / Digital
    (r'(?i)netflix', 'Netflix'),
    (r'(?i)hotstar|disney\s*\+', 'Hotstar'),
    (r'(?i)spotify', 'Spotify'),
    (r'(?i)youtube', 'YouTube'),
    (r'(?i)prime\s*video|amazon\s*prime', 'Amazon Prime'),
    (r'(?i)apple\s*services?|appleservi', 'Apple Services'),
    (r'(?i)google\s*play|googleplay|playstore', 'Google Play'),
    # Utilities
    (r'(?i)noida\s*power|npcl', 'Noida Power (NPCL)'),
    (r'(?i)indraprastha\s*gas', 'Indraprastha Gas'),
    (r'(?i)tata\s*play', 'Tata Play'),
    (r'(?i)airtel', 'Airtel'),
    (r'(?i)jio(?!\s*mart)', 'Jio'),
    # Travel
    (r'(?i)irctc', 'IRCTC'),
    (r'(?i)makemytrip', 'MakeMyTrip'),
    (r'(?i)goibibo', 'Goibibo'),
    (r'(?i)cleartrip', 'Cleartrip'),
    (r'(?i)ease\s*my\s*trip|easemytrip', 'EaseMyTrip'),
    # Finance
    (r'(?i)zerodha', 'Zerodha'),
    (r'(?i)groww', 'Groww'),
    (r'(?i)ppfas', 'PPFAS MF'),
    (r'(?i)credclub|cred\.club', 'CRED'),
    # Insurance
    (r'(?i)hdfc\s*ergo', 'HDFC Ergo'),
    (r'(?i)hdfc\s*life', 'HDFC Life'),
    (r'(?i)star\s*health', 'Star Health'),
    (r'(?i)acko', 'Acko'),
    (r'(?i)alyve\s*health', 'Alyve Health'),
]

# Pre-compile all patterns for performance
_COMPILED_CLEAN = [(re.compile(p), r) for p, r in _CLEAN_RULES]
_COMPILED_MERCHANT = [(re.compile(p), r) for p, r in _MERCHANT_RULES]


def normalize(raw: str) -> str:
    """
    Clean up a raw bank description into a human-readable merchant name.
    Steps:
    1. Apply cleaning rules (strip prefixes/suffixes, ref numbers).
    2. Try merchant rules — first match wins.
    3. Fallback: title-case the cleaned string.
    """
    if not raw or not isinstance(raw, str):
        return raw or ""

    cleaned = raw.strip()

    # Step 1: apply cleaning rules
    for pattern, replacement in _COMPILED_CLEAN:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = cleaned.strip()

    # Step 2: try merchant name rules on BOTH the original and cleaned string
    for pattern, merchant_name in _COMPILED_MERCHANT:
        if pattern.search(raw) or pattern.search(cleaned):
            return merchant_name

    # Step 3: fallback — title-case the cleaned string
    return cleaned.title() if cleaned else raw.title()
