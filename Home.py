"""
Terminator: Transaction Analyzer
Entry point — sets up page config, loads data, injects shared state for all pages.
"""

import os
import pandas as pd
import streamlit as st

from config import DATA_DIR
from utils import format_inr
from processors import load_all_transactions

st.set_page_config(
    page_title="Terminator: Transaction Analyzer",
    layout="wide",
    page_icon="💰",
)

st.title("💰 Terminator: Transaction Analyzer")
st.markdown("Analyze your expenses across credit cards, bank accounts, and payment methods")

# ---------------------------------------------------------------------------
# Load data (cached with a TTL so re-imports don't hammer the DB every run)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _load():
    return load_all_transactions()


with st.spinner("Loading and processing transactions..."):
    df_all, error_files = _load()

if df_all.empty:
    st.error("No transactions loaded. Please check your source files.")
    if error_files:
        st.subheader("Errors:")
        for err in error_files:
            st.write(f"❌ {err}")
    st.stop()

st.success(f"✅ Loaded **{len(df_all):,}** transactions")

if error_files:
    with st.expander("⚠️ Parsing Warnings"):
        for err in error_files:
            st.write(err)

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------

st.sidebar.header("🔍 Filters")

min_date = df_all['Date'].min()
max_date = df_all['Date'].max()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

categories = sorted(df_all['Category'].unique())
selected_categories = st.sidebar.multiselect("Categories", options=categories, default=categories)

payment_methods = sorted(df_all['Payment Method'].unique())
selected_payment_methods = st.sidebar.multiselect(
    "Payment Methods", options=payment_methods, default=payment_methods
)

min_amount = st.sidebar.number_input("Min Amount (₹)", value=0.0, step=100.0)
max_amount = st.sidebar.number_input(
    "Max Amount (₹)", value=float(df_all['Amount'].max()), step=1000.0
)

# Apply filters
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

df_filtered = df_all[
    (df_all['Date'] >= pd.to_datetime(start_date))
    & (df_all['Date'] <= pd.to_datetime(end_date))
    & (df_all['Category'].isin(selected_categories))
    & (df_all['Payment Method'].isin(selected_payment_methods))
    & (df_all['Amount'] >= min_amount)
    & (df_all['Amount'] <= max_amount)
]

# ---------------------------------------------------------------------------
# Share data with all pages via session_state
# ---------------------------------------------------------------------------

st.session_state["df_all"] = df_all
st.session_state["df_filtered"] = df_filtered

# ---------------------------------------------------------------------------
# Sidebar summary
# ---------------------------------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.info(f"""
**Data Summary:**
- Total Transactions: {len(df_all):,}
- Date Range: {min_date.strftime('%d %b %Y')} to {max_date.strftime('%d %b %Y')}
- Filtered Transactions: {len(df_filtered):,}
""")

# ---------------------------------------------------------------------------
# Home page quick summary (overview metrics)
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("Use the **sidebar** to navigate between pages ↖️")

col1, col2, col3, col4 = st.columns(4)
total_debit = df_filtered[df_filtered['Type'] == 'Debit']['Amount'].sum()
total_credit = df_filtered[df_filtered['Type'] == 'Credit']['Amount'].sum()
col1.metric("Total Expenses", format_inr(total_debit))
col2.metric("Total Credits", format_inr(total_credit))
col3.metric("Net", format_inr(total_credit - total_debit))
col4.metric("Transactions", f"{len(df_filtered):,}")

# ---------------------------------------------------------------------------
# Source files browser
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("📂 Source Files")

if os.path.isdir(DATA_DIR):
    folders = sorted([
        f for f in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, f)) and not f.startswith('.')
    ])
    if folders:
        for folder in folders:
            folder_path = os.path.join(DATA_DIR, folder)
            files = sorted([
                f for f in os.listdir(folder_path)
                if not f.startswith('.') and os.path.isfile(os.path.join(folder_path, f))
            ])
            label = f"**{folder}/** — {len(files)} file{'s' if len(files) != 1 else ''}"
            with st.expander(label, expanded=False):
                if files:
                    for fname in files:
                        fpath = os.path.join(folder_path, fname)
                        size_kb = os.path.getsize(fpath) / 1024
                        st.write(f"• `{fname}` — {size_kb:.1f} KB")
                else:
                    st.write("_(no files)_")
    else:
        st.info("No subfolders found in source_files/")
else:
    st.warning(f"Source files directory not found: `{DATA_DIR}`")
