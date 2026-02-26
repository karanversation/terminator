"""
Transaction Details page — searchable, filterable full transaction list.
"""

import pandas as pd
import streamlit as st

from utils import format_inr

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

display_df = df_display[['Date', 'Description', 'Amount', 'Type', 'Category', 'Payment Method', 'Source']].copy()
display_df['Date'] = pd.to_datetime(display_df['Date'])
display_df['Amount'] = display_df['Amount'].apply(format_inr)

st.info("💡 **Tip:** Use the **Sort by** dropdown above for Amount ordering. Click column headers to sort by other columns.")

st.dataframe(
    display_df,
    use_container_width=True,
    height=LARGE_TABLE_HEIGHT,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
    },
)

csv = df_display.to_csv(index=False)
st.download_button(
    label="📥 Download Filtered Data as CSV",
    data=csv,
    file_name=f"transactions_export_{selected_category_filter}_{selected_month_filter}.csv",
    mime="text/csv",
)
