"""
Category Analysis page.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr, render_txn_table

TABLE_PIXEL_HEIGHT = 40
LARGE_TABLE_HEIGHT = 1200

st.header("Category Analysis")

df_filtered = st.session_state.get("df_filtered")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded. Return to the home page.")
    st.stop()

col1, col2 = st.columns(2)

_STATS_SORT_OPTS = ["Total (High→Low)", "Total (Low→High)", "Average (High→Low)", "Count (High→Low)", "Category (A→Z)"]

def _sort_stats(df, order):
    if order == "Total (High→Low)":   return df.sort_values('Total', ascending=False)
    if order == "Total (Low→High)":   return df.sort_values('Total', ascending=True)
    if order == "Average (High→Low)": return df.sort_values('Average', ascending=False)
    if order == "Count (High→Low)":   return df.sort_values('Count', ascending=False)
    return df.sort_index()  # Category A→Z

with col1:
    st.markdown("### 💸 Expense Categories")
    category_stats_debit = df_filtered[df_filtered['Type'] == 'Debit'].groupby('Category').agg(
        {'Amount': ['sum', 'mean', 'count']}
    ).round(2)
    category_stats_debit.columns = ['Total', 'Average', 'Count']
    exp_stats_sort = st.selectbox("Sort by", _STATS_SORT_OPTS, key="exp_stats_sort")
    category_stats_debit = _sort_stats(category_stats_debit, exp_stats_sort)
    st.dataframe(
        category_stats_debit,
        use_container_width=True,
        height=TABLE_PIXEL_HEIGHT * len(category_stats_debit),
        column_config={
            "Total": st.column_config.NumberColumn("💰 Total", format="₹%.2f", width="medium"),
            "Average": st.column_config.NumberColumn("📊 Average", format="₹%.2f", width="medium"),
            "Count": st.column_config.NumberColumn("📝 Count", width="small", format="%d"),
        },
    )

with col2:
    st.markdown("### 💵 Deposit Categories")
    category_stats_credit = df_filtered[df_filtered['Type'] == 'Credit'].groupby('Category').agg(
        {'Amount': ['sum', 'mean', 'count']}
    ).round(2)
    category_stats_credit.columns = ['Total', 'Average', 'Count']
    dep_stats_sort = st.selectbox("Sort by", _STATS_SORT_OPTS, key="dep_stats_sort")
    category_stats_credit = _sort_stats(category_stats_credit, dep_stats_sort)
    st.dataframe(
        category_stats_credit,
        use_container_width=True,
        height=TABLE_PIXEL_HEIGHT * len(category_stats_credit),
        column_config={
            "Total": st.column_config.NumberColumn("💰 Total", format="₹%.2f", width="medium"),
            "Average": st.column_config.NumberColumn("📊 Average", format="₹%.2f", width="medium"),
            "Count": st.column_config.NumberColumn("📝 Count", width="small", format="%d"),
        },
    )

st.markdown("---")
st.subheader("Category Trend Over Time")

expense_totals = df_filtered[df_filtered['Type'] == 'Debit'].groupby('Category')['Amount'].sum().sort_values(ascending=False)
expense_categories = expense_totals.index.tolist()

income_totals = df_filtered[df_filtered['Type'] == 'Credit'].groupby('Category')['Amount'].sum().sort_values(ascending=False)
income_categories = income_totals.index.tolist()

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 💸 Expense Category Trend")
    if len(expense_categories) > 0:
        selected_expense_category = st.selectbox("Select Expense Category", options=expense_categories, key="expense_cat")

        expense_category_monthly = df_filtered[
            (df_filtered['Category'] == selected_expense_category) & (df_filtered['Type'] == 'Debit')
        ].groupby('Month-Year')['Amount'].sum().reset_index()

        if not expense_category_monthly.empty:
            expense_category_monthly['Amount_Formatted'] = expense_category_monthly['Amount'].apply(format_inr)
            fig = px.line(
                expense_category_monthly,
                x='Month-Year',
                y='Amount',
                title=f"{selected_expense_category} - Monthly Expenses",
                labels={'Amount': 'Expenses (₹)', 'Month-Year': 'Month'},
                markers=True,
                text='Amount_Formatted',
                custom_data=['Amount_Formatted'],
                color_discrete_sequence=['#EF553B'],
            )
            fig.update_traces(
                textposition='top center',
                hovertemplate='<b>%{x}</b><br>Amount=%{customdata[0]}<extra></extra>',
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for this category")
    else:
        st.info("No expense categories available")

with col2:
    st.markdown("#### 💵 Deposit Category Trend")
    if len(income_categories) > 0:
        selected_income_category = st.selectbox("Select Deposit Category", options=income_categories, key="income_cat")

        income_category_monthly = df_filtered[
            (df_filtered['Category'] == selected_income_category) & (df_filtered['Type'] == 'Credit')
        ].groupby('Month-Year')['Amount'].sum().reset_index()

        if not income_category_monthly.empty:
            income_category_monthly['Amount_Formatted'] = income_category_monthly['Amount'].apply(format_inr)
            fig = px.line(
                income_category_monthly,
                x='Month-Year',
                y='Amount',
                title=f"{selected_income_category} - Monthly Deposits",
                labels={'Amount': 'Deposits (₹)', 'Month-Year': 'Month'},
                markers=True,
                text='Amount_Formatted',
                custom_data=['Amount_Formatted'],
                color_discrete_sequence=['#00CC96'],
            )
            fig.update_traces(
                textposition='top center',
                hovertemplate='<b>%{x}</b><br>Amount=%{customdata[0]}<extra></extra>',
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for this category")
    else:
        st.info("No deposit categories available")

st.markdown("---")
st.subheader("All Transactions by Category")

_TXN_SORT_OPTS = ["Amount (High→Low)", "Amount (Low→High)", "Date (Newest)", "Date (Oldest)"]

def _sort_txn(df, order):
    if order == "Amount (High→Low)": return df.sort_values('Amount', ascending=False)
    if order == "Amount (Low→High)": return df.sort_values('Amount', ascending=True)
    if order == "Date (Newest)":     return df.sort_values('Date', ascending=False)
    return df.sort_values('Date', ascending=True)

expense_cat_transactions = (
    df_filtered[
        (df_filtered['Category'] == selected_expense_category) & (df_filtered['Type'] == 'Debit')
    ].copy()
    if len(expense_categories) > 0
    else pd.DataFrame()
)

income_cat_transactions = (
    df_filtered[
        (df_filtered['Category'] == selected_income_category) & (df_filtered['Type'] == 'Credit')
    ].copy()
    if len(income_categories) > 0
    else pd.DataFrame()
)

col1, col2 = st.columns(2)

with col1:
    if len(expense_categories) > 0:
        st.markdown(f"#### 💸 {selected_expense_category}")
        if not expense_cat_transactions.empty:
            st.write(f"**Total: {len(expense_cat_transactions)} transactions | {format_inr(expense_cat_transactions['Amount'].sum())}**")
            exp_cat_sort = st.selectbox("Sort by", _TXN_SORT_OPTS, key="exp_cat_sort")
            sorted_expense = _sort_txn(expense_cat_transactions, exp_cat_sort)
            render_txn_table(sorted_expense, ['Date', 'Description', 'Amount', 'Payment Method', 'Source'],
                             height=LARGE_TABLE_HEIGHT)
        else:
            st.info("No transactions in this category")

with col2:
    if len(income_categories) > 0:
        st.markdown(f"#### 💵 {selected_income_category}")
        if not income_cat_transactions.empty:
            st.write(f"**Total: {len(income_cat_transactions)} transactions | {format_inr(income_cat_transactions['Amount'].sum())}**")
            dep_cat_sort = st.selectbox("Sort by", _TXN_SORT_OPTS, key="dep_cat_sort")
            sorted_income = _sort_txn(income_cat_transactions, dep_cat_sort)
            render_txn_table(sorted_income, ['Date', 'Description', 'Amount', 'Payment Method', 'Source'],
                             height=LARGE_TABLE_HEIGHT)
        else:
            st.info("No transactions in this category")
