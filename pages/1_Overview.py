"""
Overview page — summary metrics, expense/deposit pies and bar charts.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_inr

st.header("Overview")

df_filtered = st.session_state.get("df_filtered")
if df_filtered is None or df_filtered.empty:
    st.info("No data loaded. Return to the home page.")
    st.stop()

# Key metrics
col1, col2, col3, col4 = st.columns(4)

total_debit = df_filtered[df_filtered['Type'] == 'Debit']['Amount'].sum()
total_credit = df_filtered[df_filtered['Type'] == 'Credit']['Amount'].sum()
net_expense = total_debit - total_credit
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
        hovertemplate='<b>%{y}</b><br>Amount=%{customdata[0]}<extra></extra>'
    )
    st.plotly_chart(fig_payment, use_container_width=True)

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
            hovertemplate='<b>%{y}</b><br>Amount=%{customdata[0]}<extra></extra>'
        )
        st.plotly_chart(fig_income_payment, use_container_width=True)
    else:
        st.info("No deposit data available for the selected filters.")
