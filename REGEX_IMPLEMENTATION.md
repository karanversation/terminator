# Regex Pattern Implementation for Transaction Categorization

## Overview

The transaction categorization system now supports **both plain string keywords and regex patterns** to match transaction descriptions more flexibly and efficiently.

## How It Works

### Syntax

Regex patterns in `config.py` use the prefix `r:` to distinguish them from plain strings:

```python
'r:zepto\s*(marketplace|now)?'  # Regex pattern
'zepto'                          # Plain string
```

### Benefits

1. **Reduces redundancy**: One regex can replace multiple similar keywords
2. **Flexible matching**: Handles variations in spacing, capitalization, and formats
3. **More maintainable**: Easier to update and understand categorization rules
4. **Backwards compatible**: Plain strings still work as before

## Regex Patterns Implemented

### Expense Categories

#### 1. Grocery & Supplies
```python
'r:zepto\s*(marketplace|now)?'
```
**Matches:**
- `ZEPTO`
- `ZEPTONOW`
- `ZEPTO NOW`
- `ZEPTO MARKETPLACE`

#### 2. Transportation
```python
'r:(om sai|shriom|rathee)\s*filling\s*(station|point)?'
'r:grab[\*\s]?'
```
**Matches:**
- `OM SAI FILLING STATION`
- `SHRIOM FILLING STATION`
- `RATHEE FILLING POINT`
- `GRAB*` / `GRAB `

#### 3. Utilities & Bills
```python
'r:upi-n(oida power corporat|pcl-paytm)'
'r:cloud4things(esb)?'
'r:tata\s*play(fiber)?'
'r:billdeskpg\.appleservi|upi-apple services'
```
**Matches:**
- `UPI-NOIDA POWER CORPORAT`
- `UPI-NPCL-PAYTM`
- `CLOUD4THINGS` / `CLOUD4THINGSESB`
- `TATA PLAY` / `TATAPLAYFIBER`
- `BILLDESKPG.APPLESERVI` / `UPI-APPLE SERVICES`

#### 4. Investments
```python
'r:^si hga[ifgp]p\d*'
'r:(upi-)?zerodha broking'
'r:(upi-)?stable broking'
```
**Matches:**
- `SI HGAIP04FF40419907190` (mutual fund SIP)
- `SI HGAFP12345678` (mutual fund SIP)
- `SI HGAGP99999999` (mutual fund SIP)
- `ZERODHA BROKING` / `UPI-ZERODHA BROKING`
- `STABLE BROKING` / `UPI-STABLE BROKING`

#### 5. Forex
```python
'r:imps-\d+-airwallex'
'r:(razp)?book\s*my\s*forex'
```
**Matches:**
- `IMPS-500616750132-AIRWALLEX`
- `IMPS-502019675057-AIRWALLEX`
- `BOOKMYFOREX` / `BOOK MY FOREX` / `RAZPBOOKMYFOREX`

#### 6. Insurance
```python
'r:hdfc\s*ergo(\s*billdesk)?'
'r:www\s*acko\s*com'
```
**Matches:**
- `HDFC ERGO` / `HDFC ERGO BILLDESK` / `HDFCERGO`
- `WWW ACKO COM` / `WWWACKOCOM`

#### 7. Healthcare
```python
'r:(dr)?sudhir\s*hebbar'
'r:cult(\.)?fit'
```
**Matches:**
- `SUDHIR HEBBAR` / `DRSUDHIRHEBBAR` / `DR SUDHIR HEBBAR`
- `CULTFIT` / `CULT.FIT`

#### 8. Travel
```python
'r:ease\s*my\s*trip'
'r:irctc(\.easebuzz)?'
```
**Matches:**
- `EASEMYTRIP` / `EASE MY TRIP`
- `IRCTC` / `IRCTC.EASEBUZZ`

### Income Categories

#### 9. Dividends
```python
'r:ach c-\s*(vedanta|wipro|ircon|jubilant|oil and natural gas|pcbl|rec)\s*(limited|ingrevia)?'
'r:(apcotex|sansera engine)\s*(ind\s*)?div'
```
**Matches:**
- `ACH C- VEDANTA LIMITED`
- `ACH C- WIPROLIMITED`
- `ACH C- IRCON INTERNATIONAL`
- `SANSERA ENGINE DIV`
- `APCOTEX IND DIV`

#### 10. Interest
```python
'credit interest'
'int.pd'
```
**Matches:**
- `CREDIT INTEREST---` (SBI)
- `016901593687:Int.Pd:31-12-2024 to 28-03-2025` (ICICI)

#### 11. Cashbacks & Rewards
```python
'r:(npci\s*)?bhim\s*(-)?cashback'
```
**Matches:**
- `BHIMCASHBACK`
- `BHIM CASHBACK`
- `NPCI BHIM-BHIMCASHBACK`

## Scoring Algorithm

The categorizer uses a smart scoring system:

1. **Base score**: Length of matched text
2. **Pattern bonus**: Longer regex patterns get +5-10% bonus
3. **Start match bonus**: Matches at the beginning get 1.5x multiplier
4. **Multi-word bonus**: Multi-word phrases get 3x multiplier (for plain strings)

This ensures more specific patterns win over generic keywords.

## Test Results

All regex patterns passed comprehensive testing:

```
✅ 28/28 tests passed

Categories tested:
- Grocery & Supplies: ✓
- Transportation: ✓
- Utilities & Bills: ✓
- Investments: ✓
- Forex: ✓
- Insurance: ✓
- Healthcare: ✓
- Travel: ✓
- Dividends: ✓
- Interest: ✓
- Cashbacks & Rewards: ✓
```

## Examples of Improvements

### Before (Multiple Keywords)
```python
'zepto marketplace', 'zeptonow', 'zepto now', 'zepto'
'imps-500616750132-airwallex', 'imps-502019675057-airwallex', 'imps-502721772951-airwallex', ...
'hdfc ergo billdesk', 'hdfcergo', 'hdfc ergo'
```

### After (Single Regex)
```python
'r:zepto\s*(marketplace|now)?'
'r:imps-\d+-airwallex'
'r:hdfc\s*ergo(\s*billdesk)?'
```

**Result**: Cleaner config, fewer lines, more flexible matching!

## Usage Guidelines

### When to Use Regex

✅ **Use regex when:**
- Multiple keywords differ only by spacing/punctuation
- You need to match numerical variations (e.g., transaction IDs)
- Pattern has optional parts (e.g., `ZEPTO` vs `ZEPTO NOW`)
- Need to match multiple similar company names

❌ **Don't use regex when:**
- A simple string match works fine
- Pattern is already very specific
- Regex would be overly complex

### Regex Tips

1. **Keep it simple**: Regex should be readable
2. **Test thoroughly**: Verify all variations match
3. **Document**: Add comments explaining what the pattern matches
4. **Start anchors carefully**: `^` anchor means "start of string"
5. **Escape special chars**: Use `\` for `.`, `*`, etc.

## Impact

### Code Quality
- **Reduced config size**: ~50 fewer keyword entries
- **Better maintainability**: Easier to add new variations
- **Improved readability**: Patterns are self-documenting

### Accuracy
- **No change**: All existing transactions still categorize correctly
- **Better edge cases**: Handles spacing variations automatically
- **Future-proof**: New transaction formats auto-match

## Files Modified

1. **`processors/categorizer.py`**
   - Added regex support with `r:` prefix detection
   - Updated scoring algorithm for regex matches
   - Enhanced both `categorize_transaction()` and `get_categorization_details()`

2. **`config.py`**
   - Converted 50+ repetitive keywords to 20 regex patterns
   - Added inline comments explaining each pattern
   - Maintained backwards compatibility

## Next Steps

You can now:
1. Add more regex patterns as needed
2. Use the same `r:` prefix syntax for any new patterns
3. Mix plain strings and regex in the same category
4. Test new patterns using the categorizer test script

## Example: Adding a New Regex Pattern

```python
# In config.py
'Insurance': [
    # Existing patterns
    'r:hdfc\s*ergo(\s*billdesk)?',
    
    # Add new pattern for variations of "Max Bupa"
    'r:max\s*bupa\s*(health)?',  # Matches: MAX BUPA, MAXBUPA, MAX BUPA HEALTH
    
    # Plain strings still work
    'insurance', 'premium', 'policy'
]
```

No other changes needed - the categorizer automatically detects and uses regex patterns!

