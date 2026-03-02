"""
Terminator — unified entry point.
Run with: streamlit run main.py

  localhost:8501/expense      → Expense Tracker (Overview)
  localhost:8501/networth     → Networth Overview
  localhost:8501/assets       → Networth Assets breakdown
  localhost:8501/data         → Data Sources
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Load secrets into env vars so parsers can read them at call time.
# Create .streamlit/secrets.toml (gitignored) with your passwords.
try:
    for _key in ["SBI_XLSX_PASSWORD", "CAMS_PDF_PASSWORD", "OPENAI_API_KEY"]:
        if _key not in os.environ and _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass

from processors import load_all_transactions

st.set_page_config(
    page_title="Terminator",
    page_icon="💸",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load expense data (shared across all expense pages)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _load_transactions():
    return load_all_transactions()


with st.spinner("Loading transactions..."):
    df_all, _error_files = _load_transactions()

if not df_all.empty:
    st.session_state["df_all"] = df_all
    st.session_state["df_filtered"] = df_all

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

pg = st.navigation(
    {
        "💳 Expenses": [
            st.Page("pages/1_Overview.py",      title="Overview",     url_path="expense",      icon="📊", default=True),
            st.Page("pages/2_Monthly.py",        title="Monthly",      url_path="monthly",      icon="📅"),
            st.Page("pages/3_Categories.py",     title="Categories",   url_path="categories",   icon="🏷"),
            st.Page("pages/4_Transactions.py",   title="Transactions", url_path="transactions", icon="📋"),
        ],
        "📊 Networth": [
            st.Page("networth/overview.py", title="Overview",  url_path="networth", icon="💰"),
            st.Page("networth/assets.py",   title="Assets",    url_path="assets",   icon="📈"),
        ],
        "📁 Data": [
            st.Page("pages/data_sources.py", title="Data Sources", url_path="data", icon="📁"),
        ],
    }
)
pg.run()
