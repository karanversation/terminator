"""
Monthly Analysis page.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr

TABLE_PIXEL_HEIGHT = 40

st.header("Monthly Analysis")

df_filtered = st.session_state.get("df_filtered")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded. Return to the home page.")
    st.stop()

# Monthly Balance Summary
st.subheader("💰 Monthly Balance Summary")

monthly_balance = df_filtered.groupby(['Month-Year', 'Type'])['Amount'].sum().reset_index()
monthly_balance_pivot = monthly_balance.pivot(index='Month-Year', columns='Type', values='Amount').fillna(0)
monthly_balance_pivot = monthly_balance_pivot.sort_index(ascending=False)

if 'Debit' in monthly_balance_pivot.columns:
    monthly_balance_pivot['Net (Credits - Debits)'] = (
        monthly_balance_pivot.get('Credit', 0) - monthly_balance_pivot.get('Debit', 0)
    )

st.dataframe(
    monthly_balance_pivot,
    use_container_width=True,
    height=TABLE_PIXEL_HEIGHT * len(monthly_balance_pivot),
    column_config={
        "Credit": st.column_config.NumberColumn("💵 Credits (Deposits)", format="₹%.2f", width="medium"),
        "Debit": st.column_config.NumberColumn("💸 Debits (Expenses)", format="₹%.2f", width="medium"),
        "Net (Credits - Debits)": st.column_config.NumberColumn("📊 Net Balance", format="₹%.2f", width="medium"),
    },
)

st.markdown("---")

# Monthly Trends
st.subheader("📊 Monthly Trends & Analysis")

monthly_debit_data = df_filtered[df_filtered['Type'] == 'Debit'].groupby('Month-Year')['Amount'].sum().reset_index()
monthly_debit_data['Type'] = 'Expenses'
monthly_debit_data = monthly_debit_data.sort_values('Month-Year')

monthly_credit_data = df_filtered[df_filtered['Type'] == 'Credit'].groupby('Month-Year')['Amount'].sum().reset_index()
monthly_credit_data['Type'] = 'Deposits'
monthly_credit_data = monthly_credit_data.sort_values('Month-Year')

monthly_combined = pd.concat([monthly_debit_data, monthly_credit_data], ignore_index=True)
monthly_combined['Amount_Formatted'] = monthly_combined['Amount'].apply(format_inr)

fig_combined_trend = px.line(
    monthly_combined,
    x='Month-Year',
    y='Amount',
    color='Type',
    title="Monthly Expenses & Deposits Trend",
    labels={'Amount': 'Amount (₹)', 'Month-Year': 'Month', 'Type': 'Transaction Type'},
    markers=True,
    text='Amount_Formatted',
    color_discrete_map={'Expenses': '#EF553B', 'Deposits': '#00CC96'},
    custom_data=['Amount_Formatted'],
)
fig_combined_trend.update_traces(
    textposition='top center',
    hovertemplate='<b>%{x}</b><br>Transaction Type=%{fullData.name}<br>Amount=%{customdata[0]}<extra></extra>',
)
fig_combined_trend.update_layout(hovermode='x unified')
st.plotly_chart(fig_combined_trend, use_container_width=True)

# Category breakdown
monthly_debit_category = df_filtered[df_filtered['Type'] == 'Debit'].groupby(['Month-Year', 'Category'])['Amount'].sum().reset_index()
monthly_debit_category['Type'] = 'Expenses'

monthly_credit_category = df_filtered[df_filtered['Type'] == 'Credit'].groupby(['Month-Year', 'Category'])['Amount'].sum().reset_index()
monthly_credit_category['Type'] = 'Deposits'

monthly_category_combined = pd.concat([monthly_debit_category, monthly_credit_category], ignore_index=True)

if not monthly_category_combined.empty:
    monthly_category_combined['Amount_Formatted'] = monthly_category_combined['Amount'].apply(format_inr)

    fig_category_combined = px.bar(
        monthly_category_combined,
        x='Month-Year',
        y='Amount',
        color='Category',
        facet_row='Type',
        title="Monthly Breakdown by Category",
        labels={'Amount': 'Amount (₹)', 'Month-Year': 'Month'},
        custom_data=['Amount_Formatted', 'Category'],
    )
    fig_category_combined.update_traces(
        hovertemplate='<b>%{x}</b><br>Category=%{customdata[1]}<br>Amount=%{customdata[0]}<extra></extra>'
    )
    fig_category_combined.update_yaxes(matches=None)
    fig_category_combined.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig_category_combined, use_container_width=True)

# Detailed Transactions by Month
st.markdown("---")
st.subheader("📋 Detailed Transactions by Month")

col1, col2 = st.columns([2, 1])
with col1:
    selected_month = st.selectbox(
        "Select Month",
        options=sorted(df_filtered['Month-Year'].unique(), reverse=True),
        key="common_month_selector",
    )
with col2:
    month_sort_order = st.selectbox(
        "Sort by",
        ["Amount (High)", "Amount (Low)", "Date (Newest)", "Date (Oldest)"],
        key="common_sort",
    )

debit_transactions = df_filtered[
    (df_filtered['Month-Year'] == selected_month) & (df_filtered['Type'] == 'Debit')
].copy()

credit_transactions = df_filtered[
    (df_filtered['Month-Year'] == selected_month) & (df_filtered['Type'] == 'Credit')
].copy()

for df_trans in [debit_transactions, credit_transactions]:
    if not df_trans.empty:
        if month_sort_order == "Amount (High)":
            df_trans.sort_values('Amount', ascending=False, inplace=True)
        elif month_sort_order == "Amount (Low)":
            df_trans.sort_values('Amount', ascending=True, inplace=True)
        elif month_sort_order == "Date (Newest)":
            df_trans.sort_values('Date', ascending=False, inplace=True)
        else:
            df_trans.sort_values('Date', ascending=True, inplace=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 💸 Expenses")
    if not debit_transactions.empty:
        st.write(f"**Total: {len(debit_transactions)} transactions | {format_inr(debit_transactions['Amount'].sum())}**")
        display_debit_df = debit_transactions[['Date', 'Description', 'Amount', 'Category', 'Payment Method']].copy()
        display_debit_df['Date'] = pd.to_datetime(display_debit_df['Date'])
        display_debit_df['Amount'] = display_debit_df['Amount'].apply(format_inr)
        st.dataframe(
            display_debit_df,
            use_container_width=True,
            hide_index=True,
            height=TABLE_PIXEL_HEIGHT * len(display_debit_df),
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            },
        )
    else:
        st.info(f"No expenses found for {selected_month}")

with col2:
    st.markdown("#### 💵 Deposits")
    if not credit_transactions.empty:
        st.write(f"**Total: {len(credit_transactions)} transactions | {format_inr(credit_transactions['Amount'].sum())}**")
        display_credit_df = credit_transactions[['Date', 'Description', 'Amount', 'Category', 'Payment Method']].copy()
        display_credit_df['Date'] = pd.to_datetime(display_credit_df['Date'])
        display_credit_df['Amount'] = display_credit_df['Amount'].apply(format_inr)
        st.dataframe(
            display_credit_df,
            use_container_width=True,
            hide_index=True,
            height=TABLE_PIXEL_HEIGHT * len(display_credit_df),
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            },
        )
    else:
        st.info(f"No deposits found for {selected_month}")
