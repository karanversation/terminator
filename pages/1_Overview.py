"""
Overview page — summary metrics, expense/deposit pies and bar charts.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr, render_txn_table

st.header("Overview")

df_filtered = st.session_state.get("df_filtered")
df_all = st.session_state.get("df_all")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded.")
    st.stop()

# --- Dataset stats row ---
stat1, stat2, stat3 = st.columns(3)
with stat1:
    st.metric("Transactions", f"{len(df_all):,}")
with stat2:
    min_d = df_all["Date"].min().strftime("%d %b %Y")
    max_d = df_all["Date"].max().strftime("%d %b %Y")
    st.metric("Period", f"{min_d} – {max_d}")
with stat3:
    n_months = df_all["Month-Year"].nunique()
    st.metric("Months", f"{n_months}")

st.markdown("---")

# Key metrics
col1, col2, col3, col4 = st.columns(4)

total_debit = df_filtered[df_filtered['Type'] == 'Debit']['Amount'].sum()
total_credit = df_filtered[df_filtered['Type'] == 'Credit']['Amount'].sum()
net_expense = total_credit - total_debit
avg_debit = df_filtered[df_filtered['Type'] == 'Debit']['Amount'].mean()

col1.metric("Total Expenses", format_inr(total_debit))
col2.metric("Total Credits", format_inr(total_credit))
col3.metric("Net Balance", format_inr(net_expense))
col4.metric("Avg Expense", format_inr(avg_debit))

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("💸 Expenses Overview")

    category_expenses = (
        df_filtered[df_filtered['Type'] == 'Debit']
        .groupby('Category')['Amount'].sum()
        .sort_values(ascending=False)
    )
    category_df = pd.DataFrame({
        'Category': category_expenses.index,
        'Amount': category_expenses.values,
    })
    category_df['Amount_Formatted'] = category_df['Amount'].apply(format_inr)

    fig_cat = px.pie(
        category_df,
        values='Amount',
        names='Category',
        title="Expenses by Category",
        hole=0.4,
        custom_data=['Amount_Formatted'],
    )
    fig_cat.update_traces(
        hovertemplate='<b>%{label}</b><br>Amount=%{customdata[0]}<br>Percentage=%{percent}<extra></extra>'
    )
    st.plotly_chart(fig_cat, use_container_width=True)

    payment_expenses = (
        df_filtered[df_filtered['Type'] == 'Debit']
        .groupby('Payment Method')['Amount'].sum()
        .sort_values(ascending=False)
    )
    payment_df = pd.DataFrame({
        'Payment Method': payment_expenses.index,
        'Amount': payment_expenses.values,
    })
    payment_df['Amount_Formatted'] = payment_df['Amount'].apply(format_inr)

    fig_payment = px.bar(
        payment_df,
        x='Amount',
        y='Payment Method',
        orientation='h',
        title="Expenses by Payment Method",
        labels={'Amount': 'Amount (₹)', 'Payment Method': 'Payment Method'},
        custom_data=['Amount_Formatted'],
    )
    fig_payment.update_traces(
        texttemplate='%{customdata[0]}',
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Amount=%{customdata[0]}<extra></extra>',
    )
    fig_payment.update_layout(xaxis=dict(range=[0, payment_df['Amount'].max() * 1.25]))
    st.plotly_chart(fig_payment, use_container_width=True)

    df_other_expenses = (
        df_filtered[(df_filtered['Type'] == 'Debit') & (df_filtered['Payment Method'] == 'Other')]
        .sort_values('Amount', ascending=False)
        .copy()
    )
    if not df_other_expenses.empty:
        with st.expander(f"'Other' expenses — {len(df_other_expenses)} transactions"):
            render_txn_table(df_other_expenses, ['Date', 'Description', 'Amount', 'Category'],
                             height=min(len(df_other_expenses) * 38 + 60, 500))

with col2:
    st.subheader("💵 Deposits Overview")

    category_income = (
        df_filtered[df_filtered['Type'] == 'Credit']
        .groupby('Category')['Amount'].sum()
        .sort_values(ascending=False)
    )
    if not category_income.empty:
        category_income_df = pd.DataFrame({
            'Category': category_income.index,
            'Amount': category_income.values,
        })
        category_income_df['Amount_Formatted'] = category_income_df['Amount'].apply(format_inr)

        fig_income_cat = px.pie(
            category_income_df,
            values='Amount',
            names='Category',
            title="Deposits by Category",
            hole=0.4,
            custom_data=['Amount_Formatted'],
        )
        fig_income_cat.update_traces(
            hovertemplate='<b>%{label}</b><br>Amount=%{customdata[0]}<br>Percentage=%{percent}<extra></extra>'
        )
        st.plotly_chart(fig_income_cat, use_container_width=True)
    else:
        st.info("No deposit data available for the selected filters.")

    payment_income = (
        df_filtered[df_filtered['Type'] == 'Credit']
        .groupby('Payment Method')['Amount'].sum()
        .sort_values(ascending=False)
    )
    if not payment_income.empty:
        payment_income_df = pd.DataFrame({
            'Payment Method': payment_income.index,
            'Amount': payment_income.values,
        })
        payment_income_df['Amount_Formatted'] = payment_income_df['Amount'].apply(format_inr)

        fig_income_payment = px.bar(
            payment_income_df,
            x='Amount',
            y='Payment Method',
            orientation='h',
            title="Deposits by Payment Method",
            labels={'Amount': 'Amount (₹)', 'Payment Method': 'Payment Method'},
            custom_data=['Amount_Formatted'],
        )
        fig_income_payment.update_traces(
            texttemplate='%{customdata[0]}',
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Amount=%{customdata[0]}<extra></extra>',
        )
        fig_income_payment.update_layout(xaxis=dict(range=[0, payment_income_df['Amount'].max() * 1.25]))
        st.plotly_chart(fig_income_payment, use_container_width=True)

        df_other_credits = (
            df_filtered[(df_filtered['Type'] == 'Credit') & (df_filtered['Payment Method'] == 'Other')]
            .sort_values('Amount', ascending=False)
            .copy()
        )
        if not df_other_credits.empty:
            with st.expander(f"'Other' deposits — {len(df_other_credits)} transactions"):
                render_txn_table(df_other_credits, ['Date', 'Description', 'Amount', 'Category'],
                                 height=min(len(df_other_credits) * 38 + 60, 500))
    else:
        st.info("No deposit data available for the selected filters.")
