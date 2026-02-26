"""
Category Analysis page.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr

TABLE_PIXEL_HEIGHT = 40
LARGE_TABLE_HEIGHT = 1200

st.header("Category Analysis")

df_filtered = st.session_state.get("df_filtered")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded. Return to the home page.")
    st.stop()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 💸 Expense Categories")
    category_stats_debit = df_filtered[df_filtered['Type'] == 'Debit'].groupby('Category').agg(
        {'Amount': ['sum', 'mean', 'count']}
    ).round(2)
    category_stats_debit.columns = ['Total', 'Average', 'Count']
    category_stats_debit = category_stats_debit.sort_values('Total', ascending=False)
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
    category_stats_credit = category_stats_credit.sort_values('Total', ascending=False)
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

cat_sort_order = st.selectbox(
    "Sort by",
    ["Amount (High)", "Amount (Low)", "Date (Newest)", "Date (Oldest)"],
    key="cat_sort",
)

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

for df_trans in [expense_cat_transactions, income_cat_transactions]:
    if not df_trans.empty:
        if cat_sort_order == "Amount (High)":
            df_trans.sort_values('Amount', ascending=False, inplace=True)
        elif cat_sort_order == "Amount (Low)":
            df_trans.sort_values('Amount', ascending=True, inplace=True)
        elif cat_sort_order == "Date (Newest)":
            df_trans.sort_values('Date', ascending=False, inplace=True)
        else:
            df_trans.sort_values('Date', ascending=True, inplace=True)

col1, col2 = st.columns(2)

with col1:
    if len(expense_categories) > 0:
        st.markdown(f"#### 💸 {selected_expense_category}")
        if not expense_cat_transactions.empty:
            st.write(f"**Total: {len(expense_cat_transactions)} transactions | {format_inr(expense_cat_transactions['Amount'].sum())}**")
            display_expense_df = expense_cat_transactions[['Date', 'Description', 'Amount', 'Payment Method', 'Source']].copy()
            display_expense_df['Date'] = pd.to_datetime(display_expense_df['Date'])
            display_expense_df['Amount'] = display_expense_df['Amount'].apply(format_inr)
            st.dataframe(
                display_expense_df,
                use_container_width=True,
                hide_index=True,
                height=LARGE_TABLE_HEIGHT,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                },
            )
        else:
            st.info("No transactions in this category")

with col2:
    if len(income_categories) > 0:
        st.markdown(f"#### 💵 {selected_income_category}")
        if not income_cat_transactions.empty:
            st.write(f"**Total: {len(income_cat_transactions)} transactions | {format_inr(income_cat_transactions['Amount'].sum())}**")
            display_income_df = income_cat_transactions[['Date', 'Description', 'Amount', 'Payment Method', 'Source']].copy()
            display_income_df['Date'] = pd.to_datetime(display_income_df['Date'])
            display_income_df['Amount'] = display_income_df['Amount'].apply(format_inr)
            st.dataframe(
                display_income_df,
                use_container_width=True,
                hide_index=True,
                height=LARGE_TABLE_HEIGHT,
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                },
            )
        else:
            st.info("No transactions in this category")
