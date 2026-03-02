"""
Networth Assets — detailed breakdown by asset class with inner tabs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px

from utils import format_inr
from networth.data import get_networth_data

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

with st.spinner("Loading holdings..."):
    df_all, _ = get_networth_data()

st.title("📈 Assets")

if df_all.empty:
    st.info("No holdings data found. Add files to `source_files/` subfolders.")
    st.stop()

# Latest snapshot per source
latest_dates = df_all.groupby("source")["report_date"].max()
df_latest = df_all[
    df_all.apply(lambda r: r["report_date"] == latest_dates[r["source"]], axis=1)
].copy()

# ---------------------------------------------------------------------------
# Freshness summary
# ---------------------------------------------------------------------------
freshness = (
    df_latest.groupby(["source", "asset_class"])["report_date"]
    .max()
    .reset_index()
    .sort_values("report_date", ascending=False)
)
st.caption(
    "Data as of: "
    + ", ".join(
        f"{r['source']} ({r['report_date'].strftime('%d %b %Y')})"
        for _, r in freshness.iterrows()
    )
)

# ---------------------------------------------------------------------------
# Reusable column configs
# ---------------------------------------------------------------------------
_cc_inr    = st.column_config.NumberColumn(format="₹%.0f")
_cc_date   = st.column_config.DateColumn(format="DD MMM YYYY")
_cc_units  = st.column_config.NumberColumn(format="%.4f")
_cc_shares = st.column_config.NumberColumn(format="%.0f")

# ---------------------------------------------------------------------------
# Asset tabs
# ---------------------------------------------------------------------------
(
    tab_bank, tab_eq, tab_bonds,
    tab_esop, tab_prop, tab_veh,
) = st.tabs(["🏦 Bank", "📈 Equity", "🏛 Bonds & FDs", "🔒 ESOPs", "🏠 Property", "🚗 Vehicles"])

# -------------------------------------------------------------------
# Bank Accounts
# -------------------------------------------------------------------
with tab_bank:
    df_bank = df_latest[df_latest["asset_class"] == "Bank"].copy()
    if df_bank.empty:
        st.info("No bank account data found.")
    else:
        bank_by_source = (
            df_bank.groupby("source")["value"].sum()
            .reset_index().sort_values("value", ascending=False)
        )
        tbl = df_bank[["source", "value", "report_date"]].rename(
            columns={"source": "Account", "value": "Balance", "report_date": "As of"}
        )
        if len(bank_by_source) > 1:
            col_c, col_t = st.columns([2, 1])
            with col_c:
                fig = px.bar(
                    bank_by_source, x="source", y="value", color="source",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"source": "Account", "value": "Balance (₹)"},
                )
                fig.update_traces(
                    texttemplate="₹%{y:,.0f}", textposition="outside",
                    hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                )
                fig.update_layout(showlegend=False, margin=dict(t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            with col_t:
                st.dataframe(tbl, use_container_width=True, hide_index=True,
                             column_config={"Balance": _cc_inr, "As of": _cc_date})
        else:
            st.dataframe(tbl, use_container_width=True, hide_index=True,
                         column_config={"Balance": _cc_inr, "As of": _cc_date})

# -------------------------------------------------------------------
# Equity
# -------------------------------------------------------------------
with tab_eq:
    df_eq = df_latest[df_latest["asset_class"].isin(["Stock", "Mutual Fund"])].copy()
    if df_eq.empty:
        st.info("No equity data found.")
    else:
        eq_by_source = (
            df_eq.groupby(["source", "asset_class"])["value"].sum()
            .reset_index().sort_values("value", ascending=False)
        )
        tbl_src = eq_by_source.rename(
            columns={"source": "Source", "asset_class": "Type", "value": "Value"}
        )
        if eq_by_source["source"].nunique() > 1:
            col_c, col_t = st.columns([2, 1])
            with col_c:
                fig = px.bar(
                    eq_by_source, x="source", y="value", color="asset_class",
                    barmode="stack",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"source": "Source", "value": "Value (₹)", "asset_class": "Type"},
                )
                fig.update_traces(hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
                fig.update_layout(margin=dict(t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            with col_t:
                st.dataframe(tbl_src, use_container_width=True, hide_index=True,
                             column_config={"Value": _cc_inr})
        else:
            st.dataframe(tbl_src, use_container_width=True, hide_index=True,
                         column_config={"Value": _cc_inr})

        st.markdown("---")
        st.subheader("Holdings")
        df_disp = df_eq.sort_values("value", ascending=False)[
            ["asset_class", "source", "name", "units", "price", "value", "notes"]
        ].rename(columns={
            "asset_class": "Type", "source": "Source", "name": "Name",
            "units": "Units", "price": "Price", "value": "Value (₹)", "notes": "Notes",
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True,
                     column_config={"Value (₹)": _cc_inr, "Price": _cc_inr, "Units": _cc_units})

# -------------------------------------------------------------------
# Bonds & FDs
# -------------------------------------------------------------------
with tab_bonds:
    df_bonds = df_latest[df_latest["asset_class"].isin(["Bond", "FD"])].copy()
    if df_bonds.empty:
        st.info("No bonds or FD data found.")
    else:
        bonds_by_source = (
            df_bonds.groupby(["source", "asset_class"])["value"].sum()
            .reset_index().sort_values("value", ascending=False)
        )
        tbl_b = bonds_by_source.rename(
            columns={"source": "Source", "asset_class": "Type", "value": "Value"}
        )
        if bonds_by_source["source"].nunique() > 1:
            col_c, col_t = st.columns([2, 1])
            with col_c:
                fig = px.bar(
                    bonds_by_source, x="source", y="value", color="asset_class",
                    barmode="stack",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"source": "Source", "value": "Value (₹)", "asset_class": "Type"},
                )
                fig.update_traces(hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>")
                fig.update_layout(margin=dict(t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            with col_t:
                st.dataframe(tbl_b, use_container_width=True, hide_index=True,
                             column_config={"Value": _cc_inr})
        else:
            st.dataframe(tbl_b, use_container_width=True, hide_index=True,
                         column_config={"Value": _cc_inr})

        st.markdown("---")
        st.subheader("Holdings")
        df_disp = df_bonds.sort_values("value", ascending=False)[
            ["asset_class", "source", "name", "value", "notes"]
        ].rename(columns={
            "asset_class": "Type", "source": "Source", "name": "Name",
            "value": "Value (₹)", "notes": "Notes",
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True,
                     column_config={"Value (₹)": _cc_inr})

# -------------------------------------------------------------------
# ESOPs
# -------------------------------------------------------------------
with tab_esop:
    df_esop = df_latest[df_latest["asset_class"] == "ESOP"].copy()
    if df_esop.empty:
        st.info("No ESOP data found. Add a Carta `exerciseHistory.csv` to `source_files/carta/`.")
    else:
        st.caption("Values are based on the last known Fair Market Value (FMV). Actual realisation depends on a liquidity event.")

        esop_by_source = (
            df_esop.groupby("source")["value"].sum()
            .reset_index().sort_values("value", ascending=False)
        )
        tbl_e = esop_by_source.rename(columns={"source": "Source", "value": "Value"})
        if len(esop_by_source) > 1:
            col_c, col_t = st.columns([2, 1])
            with col_c:
                fig = px.bar(
                    esop_by_source, x="source", y="value", color="source",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    labels={"source": "Source", "value": "Value (₹)"},
                )
                fig.update_traces(
                    texttemplate="₹%{y:,.0f}", textposition="outside",
                    hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                )
                fig.update_layout(showlegend=False, margin=dict(t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            with col_t:
                st.dataframe(tbl_e, use_container_width=True, hide_index=True,
                             column_config={"Value": _cc_inr})
        else:
            st.dataframe(tbl_e, use_container_width=True, hide_index=True,
                         column_config={"Value": _cc_inr})

        st.markdown("---")
        st.subheader("Holdings")
        df_disp = df_esop.sort_values("value", ascending=False)[
            ["source", "name", "units", "price", "value", "notes"]
        ].rename(columns={
            "source": "Source", "name": "Company", "units": "Shares",
            "price": "Price/Share (₹)", "value": "Value (₹)", "notes": "Notes",
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True,
                     column_config={
                         "Value (₹)": _cc_inr,
                         "Price/Share (₹)": _cc_inr,
                         "Shares": _cc_shares,
                     })

# -------------------------------------------------------------------
# Property
# -------------------------------------------------------------------
with tab_prop:
    df_prop = df_latest[df_latest["asset_class"] == "Property"].copy()
    if df_prop.empty:
        st.info("No property data found. Add `.txt` files to `source_files/property/`.")
    else:
        st.caption("Values are net of ownership % and outstanding loan. Update `.txt` files in `source_files/property/` to refresh.")
        df_disp = df_prop.sort_values("value", ascending=False)[
            ["name", "value", "report_date", "notes"]
        ].rename(columns={
            "name": "Property", "value": "Est. Value (₹)",
            "report_date": "As of", "notes": "Notes",
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True,
                     column_config={"Est. Value (₹)": _cc_inr, "As of": _cc_date})

# -------------------------------------------------------------------
# Vehicles
# -------------------------------------------------------------------
with tab_veh:
    df_veh = df_latest[df_latest["asset_class"] == "Vehicle"].copy()
    if df_veh.empty:
        st.info("No vehicle data found. Add `.txt` files to `source_files/vehicles/`.")
    else:
        st.caption("Values are estimated resale prices. Update `value` and `date` in each file to refresh.")
        df_disp = df_veh.sort_values("value", ascending=False)[
            ["name", "value", "report_date", "notes"]
        ].rename(columns={
            "name": "Vehicle", "value": "Est. Resale Value (₹)",
            "report_date": "As of", "notes": "Notes",
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True,
                     column_config={"Est. Resale Value (₹)": _cc_inr, "As of": _cc_date})
