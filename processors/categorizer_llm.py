"""
LLM-based transaction categorizer using Claude Haiku.
Falls back to rule-based categorization if ANTHROPIC_API_KEY is not set.
Results are cached in the DB by normalized description to avoid repeat calls.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50


def _get_all_categories() -> list[str]:
    """Return combined list of expense + income categories."""
    import yaml
    cats_path = os.path.join(os.path.dirname(__file__), '..', 'categories.yaml')
    try:
        with open(cats_path) as f:
            data = yaml.safe_load(f)
        expense = list(data.get('expense_categories', {}).keys())
        income = list(data.get('income_categories', {}).keys())
        # Deduplicate, preserve order
        seen = set()
        result = []
        for c in expense + income:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result
    except Exception:
        return [
            'Grocery & Supplies', 'Food & Dining', 'Transportation',
            'Shopping', 'Utilities & Bills', 'Rent', 'Healthcare',
            'Travel', 'Investments', 'Forex', 'Credit Card Payment',
            'ATM Withdrawal', 'Transfers', 'Entertainment', 'Taxes',
            'Insurance', 'Education', 'Fees & Charges', 'Salaries',
            'Salary', 'Dividends', 'Interest', 'Cashbacks & Rewards',
            'Refunds & Reversals', 'Rent Received', 'Miscellaneous',
        ]


def categorize_batch_llm(
    descriptions: list[str],
    categories: Optional[list[str]] = None,
) -> list[dict]:
    """
    Categorize a batch of transaction descriptions using Claude Haiku.
    Returns a list of dicts: [{description, category, confidence}].
    Falls back to rule-based if ANTHROPIC_API_KEY is not set.
    """
    if categories is None:
        categories = _get_all_categories()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set — using rule-based fallback")
        return _rule_based_fallback(descriptions)

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — using rule-based fallback")
        return _rule_based_fallback(descriptions)

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    # Process in batches
    for i in range(0, len(descriptions), _BATCH_SIZE):
        batch = descriptions[i: i + _BATCH_SIZE]
        batch_results = _call_llm(client, batch, categories)
        results.extend(batch_results)

    return results


def _call_llm(client, descriptions: list[str], categories: list[str]) -> list[dict]:
    """Call Claude Haiku with a single batch."""
    cat_list = ", ".join(categories)
    txn_list = json.dumps([{"description": d} for d in descriptions], ensure_ascii=False)

    prompt = f"""You are categorizing Indian bank/credit card transactions.

Categories: {cat_list}

Rules:
- UPI payments to individual person names → Transfers
- If confidence < 0.7 → use Miscellaneous
- Return ONLY valid JSON, no extra text

Transactions:
{txn_list}

Return JSON array: [{{"description": "...", "category": "...", "confidence": 0.0}}]"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()

        # Extract JSON array from response
        start = text.find('[')
        end = text.rfind(']') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON array found in response")

        parsed = json.loads(text[start:end])
        return parsed

    except Exception as e:
        logger.error(f"LLM categorization failed: {e}")
        return _rule_based_fallback(descriptions)


def _rule_based_fallback(descriptions: list[str]) -> list[dict]:
    """Use the existing rule-based categorizer as fallback."""
    from .categorizer import categorize_transaction
    results = []
    for desc in descriptions:
        cat = categorize_transaction(desc, 'Debit')
        results.append({
            "description": desc,
            "category": cat,
            "confidence": 0.8 if cat != 'Miscellaneous' else 0.3,
        })
    return results


def categorize_new_transactions(conn, rules=None) -> int:
    """
    Categorize uncategorized transactions in the DB.

    1. Load rows where category IS NULL or 'Miscellaneous'.
    2. Group by normalized description — reuse cached category for known descriptions.
    3. Send unknowns to LLM in batches.
    4. Write results back to DB with category_source='llm'.

    Returns the number of rows updated.
    """
    from db import get_uncategorized, update_category

    df = get_uncategorized(conn)
    if df.empty:
        return 0

    categories = _get_all_categories()

    # Group by description to avoid re-querying the same merchant
    desc_col = 'description' if 'description' in df.columns else 'raw_description'
    unique_descs = df[desc_col].dropna().unique().tolist()

    if not unique_descs:
        return 0

    results = categorize_batch_llm(unique_descs, categories)

    # Build lookup: description → category
    lookup = {r['description']: r for r in results if isinstance(r, dict)}

    updated = 0
    for _, row in df.iterrows():
        desc = row.get(desc_col, '')
        if desc in lookup:
            cat = lookup[desc].get('category', 'Miscellaneous')
            confidence = lookup[desc].get('confidence', 0.5)
            if confidence >= 0.7 and cat != 'Miscellaneous':
                update_category(conn, row['id'], cat, source='llm')
                updated += 1

    return updated
