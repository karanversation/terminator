"""
Data Sources — unified view of all source files for both apps.
Shows expense source folders, networth source folders, and any parse errors.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from processors import load_all_transactions
from networth.loader import load_all_holdings, get_source_status

DATA_DIR = Path("source_files")
_SUPPORTED_EXT = {".csv", ".xlsx", ".xls", ".txt", ".pdf"}

# ---------------------------------------------------------------------------
# Cached loaders (reuses results already computed by the other pages)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def _expense():
    return load_all_transactions()

@st.cache_data(ttl=300, show_spinner=False)
def _networth():
    return load_all_holdings()


def _files(folder: Path):
    if not folder.exists():
        return []
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in _SUPPORTED_EXT)


def _last_modified(files):
    if not files:
        return "—"
    return datetime.fromtimestamp(max(f.stat().st_mtime for f in files)).strftime("%d %b %Y")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("📁 Data Sources")

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Checking sources..."):
    _, expense_errors = _expense()
    nw_df, nw_errors = _networth()

# ---------------------------------------------------------------------------
# Monthly Coverage Matrix — shown first
# ---------------------------------------------------------------------------

st.subheader("📅 Monthly Coverage by Source")

df_all = st.session_state.get("df_all")
if df_all is not None and not df_all.empty:
    coverage = (
        df_all.groupby(["Month-Year", "Source"])
        .size()
        .reset_index(name="count")
    )
    pivot = coverage.pivot(index="Month-Year", columns="Source", values="count").fillna(0)
    pivot = pivot.sort_index(ascending=False)

    short_names = {
        "HDFC Diners Black CC":  "HDFC Diners",
        "HDFC Regalia CC":       "HDFC Regalia",
        "HDFC Savings Account":  "HDFC Savings",
        "ICICI Amazon Pay CC":   "ICICI Amzn CC",
        "ICICI Savings Account": "ICICI Savings",
        "SBI Account":           "SBI",
    }
    pivot = pivot.rename(columns=short_names)

    def _color_cell(val):
        if val > 0:
            return "background-color: #1a7a4a; color: white; text-align: center;"
        return "background-color: #2b2b2b; color: #555; text-align: center;"

    def _fmt(val):
        return str(int(val)) if val > 0 else "—"

    styled = pivot.style.format(_fmt).applymap(_color_cell)
    st.dataframe(styled, use_container_width=True, height=40 * (len(pivot) + 1))
else:
    st.info("No transaction data loaded yet. Load data from the home page first.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Expense Sources  |  Networth Sources  (side by side)
# ---------------------------------------------------------------------------

EXPENSE_FOLDERS = [
    ("HDFC Credit Cards",    "hdfc_cc",       "Diners Black (*_2508) & Regalia"),
    ("HDFC Savings",         "hdfc_savings",  "Shared with Networth bank balance"),
    ("ICICI Amazon Pay CC",  "icici_cc",      ""),
    ("ICICI Savings",        "icici_savings", "Shared with Networth bank balance"),
    ("SBI Savings",          "sbi",           "Shared with Networth bank balance"),
]

# Latest data date per networth source from DB
latest_by_source = {}
if not nw_df.empty:
    for source, grp in nw_df.groupby("source"):
        latest_by_source[source] = grp["report_date"].max().strftime("%d %b %Y")

col_exp, col_nw = st.columns(2)

with col_exp:
    st.subheader("💳 Expense Sources")
    exp_rows = []
    for source, folder, note in EXPENSE_FOLDERS:
        files = _files(DATA_DIR / folder)
        exp_rows.append({
            "Source":        source,
            "Folder":        f"source_files/{folder}/",
            "Files":         len(files),
            "Last Modified": _last_modified(files),
            "Note":          note,
        })
    st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

    for source, folder, _ in EXPENSE_FOLDERS:
        files = _files(DATA_DIR / folder)
        label = f"`source_files/{folder}/` — {len(files)} file{'s' if len(files) != 1 else ''}"
        with st.expander(label, expanded=False):
            if files:
                for f in files:
                    st.write(f"• `{f.name}` — {f.stat().st_size / 1024:.1f} KB")
            else:
                st.write("_(no files)_")

with col_nw:
    st.subheader("📊 Networth Sources")
    nw_rows = []
    for s in get_source_status():
        db_key = s["source"].replace(" (Bank Balance)", "").strip()
        nw_rows.append({
            "Source":      s["source"],
            "Folder":      s["folder"],
            "Files":       s["file_count"],
            "Status":      "✅ Found" if s["exists"] else "📁 Not found",
            "Latest Data": latest_by_source.get(db_key, "—"),
        })
    st.dataframe(pd.DataFrame(nw_rows), use_container_width=True, hide_index=True)

    for s in get_source_status():
        if not s["exists"]:
            continue
        files = _files(Path(s["folder"]))
        label = f"`{s['folder']}/` — {len(files)} file{'s' if len(files) != 1 else ''}"
        with st.expander(label, expanded=False):
            if files:
                for f in files:
                    st.write(f"• `{f.name}` — {f.stat().st_size / 1024:.1f} KB")
            else:
                st.write("_(no files)_")

st.markdown("---")

# ---------------------------------------------------------------------------
# Parse Errors
# ---------------------------------------------------------------------------

all_errors = list(expense_errors) + list(nw_errors)
st.subheader("Parse Errors")
if all_errors:
    for err in all_errors:
        st.warning(err)
else:
    st.success("✅ All files parsed successfully — no errors.")
