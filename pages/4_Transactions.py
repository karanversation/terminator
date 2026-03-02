"""
Transactions page — searchable transaction list + unclassified review at the bottom.
"""
import os
import pandas as pd
import streamlit as st

from db import init_db, update_category, get_uncategorized
from processors.categorizer_llm import categorize_batch_llm
from utils import format_inr, render_txn_table

LARGE_TABLE_HEIGHT = 1200

st.header("Transaction Details")
st.markdown("### 🔍 View All Transactions by Category or Month")

df_filtered = st.session_state.get("df_filtered")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded. Return to the home page.")
    st.stop()

col1, col2, col3 = st.columns(3)

with col1:
    all_categories = ['All Categories'] + sorted(df_filtered['Category'].unique().tolist())
    selected_category_filter = st.selectbox("Filter by Category", options=all_categories, key="detail_category_filter")

with col2:
    all_months = ['All Months'] + sorted(df_filtered['Month-Year'].unique().tolist(), reverse=True)
    selected_month_filter = st.selectbox("Filter by Month", options=all_months, key="detail_month_filter")

with col3:
    type_options = ['All Types', 'Debit Only', 'Credit Only']
    selected_type_filter = st.selectbox("Transaction Type", options=type_options, key="detail_type_filter")

search_term = st.text_input("🔍 Search in descriptions", placeholder="Enter keywords...")

df_display = df_filtered.copy()

if selected_category_filter != 'All Categories':
    df_display = df_display[df_display['Category'] == selected_category_filter]

if selected_month_filter != 'All Months':
    df_display = df_display[df_display['Month-Year'] == selected_month_filter]

if selected_type_filter == 'Debit Only':
    df_display = df_display[df_display['Type'] == 'Debit']
elif selected_type_filter == 'Credit Only':
    df_display = df_display[df_display['Type'] == 'Credit']

if search_term:
    df_display = df_display[df_display['Description'].str.contains(search_term, case=False, na=False)]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Transactions", f"{len(df_display):,}")
with col2:
    st.metric("Total Expenses", format_inr(df_display[df_display['Type'] == 'Debit']['Amount'].sum()))
with col3:
    st.metric("Total Credits", format_inr(df_display[df_display['Type'] == 'Credit']['Amount'].sum()))
with col4:
    st.metric("Avg Amount", format_inr(df_display['Amount'].mean()))

st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"**Showing all {len(df_display):,} transactions**")
with col2:
    sort_order = st.selectbox(
        "Sort by",
        ["Date (Newest)", "Date (Oldest)", "Amount (High to Low)", "Amount (Low to High)"],
    )

if sort_order == "Date (Newest)":
    df_display = df_display.sort_values('Date', ascending=False)
elif sort_order == "Date (Oldest)":
    df_display = df_display.sort_values('Date', ascending=True)
elif sort_order == "Amount (High to Low)":
    df_display = df_display.sort_values('Amount', ascending=False)
else:
    df_display = df_display.sort_values('Amount', ascending=True)

df_display = df_display.reset_index(drop=True)

st.info("💡 **Tip:** Use the **Sort by** dropdown above for ordering. Hover over a description to see the raw bank text.")

render_txn_table(
    df_display,
    ['Date', 'Description', 'Amount', 'Type', 'Category', 'Payment Method', 'Source'],
    height=LARGE_TABLE_HEIGHT,
)

csv = df_display.to_csv(index=False)
st.download_button(
    label="📥 Download Filtered Data as CSV",
    data=csv,
    file_name=f"transactions_export_{selected_category_filter}_{selected_month_filter}.csv",
    mime="text/csv",
)

# ---------------------------------------------------------------------------
# Unclassified Transactions Review
# ---------------------------------------------------------------------------

def _get_all_categories() -> list:
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


st.markdown("---")
st.subheader("🔍 Unclassified Transactions")

ALL_CATEGORIES = _get_all_categories()

conn = init_db()
df_uncategorized = get_uncategorized(conn)

if df_uncategorized.empty:
    st.success("All transactions are categorized!")
    conn.close()
else:
    st.metric("Transactions needing review", len(df_uncategorized))

    st.subheader("🤖 AI category suggestions")
    st.caption("Get AI-suggested categories for the dropdowns below. You can edit any suggestion and click **Save corrections** to persist.")

    # Show persistent feedback from previous AI run (survives rerun)
    if '_ai_feedback' in st.session_state:
        level, msg = st.session_state.pop('_ai_feedback')
        if level == 'success':
            st.success(msg)
        elif level == 'error':
            st.error(msg)
        else:
            st.info(msg)

    if st.button("Suggest categories with AI", type="secondary"):
        if not os.environ.get("OPENAI_API_KEY"):
            st.session_state['_ai_feedback'] = ('error', "OPENAI_API_KEY is not set in your environment.")
            st.rerun()
        else:
            desc_col = 'description' if 'description' in df_uncategorized.columns else 'raw_description'
            unique_descs = df_uncategorized[desc_col].dropna().unique().tolist()
            if unique_descs:
                try:
                    results = categorize_batch_llm(unique_descs, ALL_CATEGORIES)
                    suggestions = {}
                    for r in results:
                        if isinstance(r, dict) and r.get('confidence', 0) >= 0.7 and r.get('category') and r.get('category') != 'Miscellaneous':
                            suggestions[r['description']] = r['category']
                    if suggestions:
                        updated = 0
                        for _, row in df_uncategorized.iterrows():
                            txn_id = row['id']
                            norm_desc = row.get('description', '') or row.get('raw_description', '')
                            raw_desc  = row.get('raw_description', '')
                            suggested = suggestions.get(norm_desc) or suggestions.get(raw_desc)
                            if suggested and suggested in ALL_CATEGORIES:
                                st.session_state[f"cat_{txn_id}"] = suggested
                                updated += 1
                        st.session_state['_ai_feedback'] = ('success', f"Updated dropdowns for **{updated}** transaction(s). Review and click **Save corrections** to save.")
                    else:
                        st.session_state['_ai_feedback'] = ('info', "No high-confidence suggestions returned.")
                except Exception as e:
                    st.session_state['_ai_feedback'] = ('error', f"AI categorization failed: {e}")
                st.rerun()
            else:
                st.warning("No descriptions to suggest for.")

    st.markdown("---")
    st.subheader("Review & Correct Categories")
    st.caption("Select the correct category for each transaction, then click **Save corrections**.")

    _sort_opts = {
        "Date (Newest first)":   ("date",        False),
        "Date (Oldest first)":   ("date",        True),
        "Name (A → Z)":          ("description", True),
        "Name (Z → A)":          ("description", False),
        "Amount (High → Low)":   ("amount",      False),
        "Amount (Low → High)":   ("amount",      True),
    }
    review_sort = st.selectbox("Sort by", list(_sort_opts.keys()), key="review_sort")
    sort_col, sort_asc = _sort_opts[review_sort]
    df_uncategorized = df_uncategorized.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

    corrections = {}

    with st.form("review_form"):
        for idx, row in df_uncategorized.iterrows():
            txn_id = row['id']
            raw_desc = row.get('raw_description', '') or ''
            norm_desc = row.get('description', '') or raw_desc
            amount = row.get('amount', 0)
            txn_type = row.get('type', '')
            current_cat = row.get('category', 'Miscellaneous') or 'Miscellaneous'
            date_str = pd.to_datetime(row['date']).strftime('%d %b %Y') if 'date' in row else ''

            # Initialise session state key with current category only on first render;
            # AI suggestions write to this key directly, so we must not also pass index=
            widget_key = f"cat_{txn_id}"
            if widget_key not in st.session_state:
                st.session_state[widget_key] = current_cat

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
                    key=widget_key,
                    label_visibility="collapsed",
                )
                corrections[txn_id] = new_cat

            st.divider()

        submitted = st.form_submit_button("💾 Save corrections", type="primary")

    if submitted:
        saved = 0
        for txn_id, new_cat in corrections.items():
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
            if 'df_all' in st.session_state:
                del st.session_state['df_all']
        else:
            st.info("No changes were made.")

    conn.close()
