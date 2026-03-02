"""
Monthly Analysis page.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr, render_txn_table

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

if 'Debit' in monthly_balance_pivot.columns:
    monthly_balance_pivot['Net (Credits - Debits)'] = (
        monthly_balance_pivot.get('Credit', 0) - monthly_balance_pivot.get('Debit', 0)
    )

_bal_sort_opts = ["Month (Newest)", "Month (Oldest)"]
if 'Credit' in monthly_balance_pivot.columns:
    _bal_sort_opts += ["Credits (High→Low)", "Credits (Low→High)"]
if 'Debit' in monthly_balance_pivot.columns:
    _bal_sort_opts += ["Debits (High→Low)", "Debits (Low→High)"]
if 'Net (Credits - Debits)' in monthly_balance_pivot.columns:
    _bal_sort_opts += ["Net Balance (High→Low)", "Net Balance (Low→High)"]

_sc1, _sc2 = st.columns([3, 1])
with _sc2:
    bal_sort = st.selectbox("Sort by", _bal_sort_opts, key="bal_sort")

if bal_sort == "Month (Newest)":
    monthly_balance_pivot = monthly_balance_pivot.sort_index(ascending=False)
elif bal_sort == "Month (Oldest)":
    monthly_balance_pivot = monthly_balance_pivot.sort_index(ascending=True)
elif bal_sort == "Credits (High→Low)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Credit', ascending=False)
elif bal_sort == "Credits (Low→High)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Credit', ascending=True)
elif bal_sort == "Debits (High→Low)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Debit', ascending=False)
elif bal_sort == "Debits (Low→High)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Debit', ascending=True)
elif bal_sort == "Net Balance (High→Low)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Net (Credits - Debits)', ascending=False)
elif bal_sort == "Net Balance (Low→High)":
    monthly_balance_pivot = monthly_balance_pivot.sort_values('Net (Credits - Debits)', ascending=True)

def _rdylgn(val, col_min, col_max, reverse=False):
    """Return a pastel CSS background-color on a red→yellow→green gradient."""
    if col_max == col_min:
        t = 0.5
    else:
        t = (val - col_min) / (col_max - col_min)
    if reverse:
        t = 1 - t
    # Dark-theme palette: muted red → amber → muted green
    if t <= 0.5:
        t2 = t * 2
        r = int(150 + t2 * (150 - 150))   # 150 → 150
        g = int(45  + t2 * (125 - 45))    # 45  → 125
        b = int(45  + t2 * (40  - 45))    # 45  → 40
    else:
        t2 = (t - 0.5) * 2
        r = int(150 + t2 * (40  - 150))   # 150 → 40
        g = int(125 + t2 * (140 - 125))   # 125 → 140
        b = int(40  + t2 * (70  - 40))    # 40  → 70
    return f"background-color: rgb({r},{g},{b}); color: #eee"

def _apply_gradient(series, reverse=False):
    lo, hi = series.min(), series.max()
    return [_rdylgn(v, lo, hi, reverse=reverse) for v in series]

fmt = {col: format_inr for col in monthly_balance_pivot.columns}
styler = monthly_balance_pivot.style.format(fmt)
if 'Credit' in monthly_balance_pivot.columns:
    styler = styler.apply(_apply_gradient, subset=['Credit'], reverse=False)
if 'Debit' in monthly_balance_pivot.columns:
    styler = styler.apply(_apply_gradient, subset=['Debit'], reverse=True)
if 'Net (Credits - Debits)' in monthly_balance_pivot.columns:
    styler = styler.apply(_apply_gradient, subset=['Net (Credits - Debits)'], reverse=False)

st.dataframe(
    styler,
    use_container_width=True,
    height=TABLE_PIXEL_HEIGHT * len(monthly_balance_pivot),
    column_config={
        "Credit": st.column_config.Column("💵 Credits (Deposits)", width="medium"),
        "Debit": st.column_config.Column("💸 Debits (Expenses)", width="medium"),
        "Net (Credits - Debits)": st.column_config.Column("📊 Net Balance", width="medium"),
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

selected_month = st.selectbox(
    "Select Month",
    options=sorted(df_filtered['Month-Year'].unique(), reverse=True),
    key="common_month_selector",
)

_SORT_OPTS = ["Amount (High→Low)", "Amount (Low→High)", "Date (Newest)", "Date (Oldest)"]

def _sort_df(df, order):
    if order == "Amount (High→Low)":
        return df.sort_values('Amount', ascending=False)
    elif order == "Amount (Low→High)":
        return df.sort_values('Amount', ascending=True)
    elif order == "Date (Newest)":
        return df.sort_values('Date', ascending=False)
    else:
        return df.sort_values('Date', ascending=True)

debit_transactions = df_filtered[
    (df_filtered['Month-Year'] == selected_month) & (df_filtered['Type'] == 'Debit')
].copy()

credit_transactions = df_filtered[
    (df_filtered['Month-Year'] == selected_month) & (df_filtered['Type'] == 'Credit')
].copy()

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 💸 Expenses")
    if not debit_transactions.empty:
        st.write(f"**Total: {len(debit_transactions)} transactions | {format_inr(debit_transactions['Amount'].sum())}**")
        exp_sort = st.selectbox("Sort by", _SORT_OPTS, key="exp_month_sort")
        sorted_debit = _sort_df(debit_transactions, exp_sort)
        render_txn_table(sorted_debit, ['Date', 'Description', 'Amount', 'Category', 'Payment Method'],
                         height=min(len(sorted_debit) * 38 + 60, 700))
    else:
        st.info(f"No expenses found for {selected_month}")

with col2:
    st.markdown("#### 💵 Deposits")
    if not credit_transactions.empty:
        st.write(f"**Total: {len(credit_transactions)} transactions | {format_inr(credit_transactions['Amount'].sum())}**")
        dep_sort = st.selectbox("Sort by", _SORT_OPTS, key="dep_month_sort")
        sorted_credit = _sort_df(credit_transactions, dep_sort)
        render_txn_table(sorted_credit, ['Date', 'Description', 'Amount', 'Category', 'Payment Method'],
                         height=min(len(sorted_credit) * 38 + 60, 700))
    else:
        st.info(f"No deposits found for {selected_month}")
