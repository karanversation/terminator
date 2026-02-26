"""
Manual Category Review page.
Shows uncategorized / Miscellaneous transactions and lets the user correct them.
Corrections are persisted to the SQLite DB.
"""

import pandas as pd
import streamlit as st

from db import init_db, update_category, get_uncategorized
from utils import format_inr
from processors.categorizer_llm import categorize_batch_llm

st.header("Category Review")

# Load available categories for the dropdown
def _get_all_categories() -> list[str]:
    import os
    import yaml
    cats_path = os.path.join(os.path.dirname(__file__), '..', 'categories.yaml')
    try:
        with open(cats_path) as f:
            data = yaml.safe_load(f)
        expense = list(data.get('expense_categories', {}).keys())
        income = list(data.get('income_categories', {}).keys())
        seen: set = set()
        result = []
        for c in expense + income:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return sorted(result)
    except Exception:
        return sorted([
            'Grocery & Supplies', 'Food & Dining', 'Transportation',
            'Shopping', 'Utilities & Bills', 'Rent', 'Healthcare',
            'Travel', 'Investments', 'Forex', 'Credit Card Payment',
            'ATM Withdrawal', 'Transfers', 'Entertainment', 'Taxes',
            'Insurance', 'Education', 'Fees & Charges', 'Salaries',
            'Salary', 'Dividends', 'Interest', 'Cashbacks & Rewards',
            'Refunds & Reversals', 'Rent Received', 'Miscellaneous',
        ])


ALL_CATEGORIES = _get_all_categories()

conn = init_db()
df_uncategorized = get_uncategorized(conn)

if df_uncategorized.empty:
    st.success("All transactions are categorized!")
    conn.close()
    st.stop()

st.metric("Transactions needing review", len(df_uncategorized))
st.markdown("---")

# Explicit trigger for LLM suggestions (dropdown only; user saves explicitly)
st.subheader("🤖 AI category suggestions")
st.caption("Get AI-suggested categories for the dropdowns below. You can edit any suggestion and click **Save corrections** to persist.")
if st.button("Suggest categories with AI", type="secondary"):
    desc_col = 'description' if 'description' in df_uncategorized.columns else 'raw_description'
    unique_descs = df_uncategorized[desc_col].dropna().unique().tolist()
    if unique_descs:
        results = categorize_batch_llm(unique_descs, ALL_CATEGORIES)
        suggestions = {}
        for r in results:
            if isinstance(r, dict) and r.get('confidence', 0) >= 0.7 and r.get('category') and r.get('category') != 'Miscellaneous':
                suggestions[r['description']] = r['category']
        if suggestions:
            st.session_state['review_ai_suggestions'] = suggestions
            st.success(f"Filled dropdowns for **{len(suggestions)}** unique description(s). Review and click **Save corrections** to save.")
        else:
            st.info("No high-confidence suggestions returned. (Check `OPENAI_API_KEY` or try again.)")
        st.rerun()
    else:
        st.warning("No descriptions to suggest for.")

st.markdown("---")

# Build an editable form
st.subheader("Review & Correct Categories")
st.caption("Select the correct category for each transaction, then click **Save corrections**.")

# Show transactions sorted by date descending
df_uncategorized = df_uncategorized.sort_values('date', ascending=False).reset_index(drop=True)

display_cols = ['date', 'raw_description', 'description', 'amount', 'type', 'account', 'category']
available_cols = [c for c in display_cols if c in df_uncategorized.columns]
df_show = df_uncategorized[available_cols].copy()

if 'date' in df_show.columns:
    df_show['date'] = pd.to_datetime(df_show['date']).dt.strftime('%d %b %Y')

corrections: dict[str, str] = {}

with st.form("review_form"):
    for idx, row in df_uncategorized.iterrows():
        txn_id = row['id']
        raw_desc = row.get('raw_description', '') or ''
        norm_desc = row.get('description', '') or raw_desc
        amount = row.get('amount', 0)
        txn_type = row.get('type', '')
        current_cat = row.get('category', 'Miscellaneous') or 'Miscellaneous'
        # Use AI suggestion for dropdown default if we have one for this description
        ai_suggestions = st.session_state.get('review_ai_suggestions') or {}
        default_cat = ai_suggestions.get(norm_desc) or ai_suggestions.get(raw_desc) or current_cat
        default_idx = ALL_CATEGORIES.index(default_cat) if default_cat in ALL_CATEGORIES else len(ALL_CATEGORIES) - 1
        date_str = pd.to_datetime(row['date']).strftime('%d %b %Y') if 'date' in row else ''

        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(
                f"**{date_str}** — {norm_desc or raw_desc}  \n"
                f"<small>{raw_desc}</small>  \n"
                f"`{txn_type}` · {format_inr(amount)}",
                unsafe_allow_html=True,
            )
        with col2:
            new_cat = st.selectbox(
                "Category",
                options=ALL_CATEGORIES,
                index=default_idx,
                key=f"cat_{txn_id}",
                label_visibility="collapsed",
            )
            corrections[txn_id] = new_cat

        st.divider()

    submitted = st.form_submit_button("💾 Save corrections", type="primary")

if submitted:
    saved = 0
    for txn_id, new_cat in corrections.items():
        # Find original category
        orig_rows = df_uncategorized[df_uncategorized['id'] == txn_id]
        if orig_rows.empty:
            continue
        orig_cat = orig_rows.iloc[0].get('category', 'Miscellaneous') or 'Miscellaneous'
        if new_cat != orig_cat:
            update_category(conn, txn_id, new_cat, source='manual')
            saved += 1

    if 'review_ai_suggestions' in st.session_state:
        del st.session_state['review_ai_suggestions']
    if saved:
        st.success(f"Saved {saved} correction(s). Refresh the page to see updated results.")
        # Invalidate cached data so main page reloads fresh
        if 'df_all' in st.session_state:
            del st.session_state['df_all']
    else:
        st.info("No changes were made.")

conn.close()
