"""
Networth Tracker — entry point.
Run with: streamlit run networth/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path so all existing modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px

from utils import format_inr
from networth.loader import load_all_holdings

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_data():
    df, errors = load_all_holdings()
    return df, errors


with st.spinner("Loading holdings..."):
    df_all, load_errors = get_data()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📊 Networth Tracker")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2 = st.tabs(["Current Snapshot", "Historical Trend"])

# ===========================================================================
# TAB 1: Current Snapshot
# ===========================================================================

with tab1:
    if df_all.empty:
        st.info(
            "No holdings data found. Add files to `source_files/` subfolders "
            "or ensure savings statement files exist for bank balances."
        )
    else:
        # For each source, take all rows from its latest report_date
        latest_dates = df_all.groupby("source")["report_date"].max()
        df_latest = df_all[
            df_all.apply(lambda r: r["report_date"] == latest_dates[r["source"]], axis=1)
        ].copy()

        # ---------------------------------------------------------------
        # Controls
        # ---------------------------------------------------------------
        ctrl_col1, ctrl_col2, _ = st.columns([1, 1, 2])
        with ctrl_col1:
            haircut_pct = st.slider("ESOP Haircut", 0, 80, 30, 5, format="%d%%",
                                    help="Discount applied to illiquid ESOP valuations")
        with ctrl_col2:
            include_vehicles = st.checkbox(
                "Include Lifestyle Assets in total", value=False,
                help="Vehicles are lifestyle/depreciating assets — toggle to include in networth"
            )

        # ---------------------------------------------------------------
        # Bucket raw values
        # ---------------------------------------------------------------
        df_bank = df_latest[df_latest["asset_class"] == "Bank"]
        df_equity = df_latest[df_latest["asset_class"].isin(["Stock", "Mutual Fund"])]
        df_bonds = df_latest[df_latest["asset_class"].isin(["Bond", "FD"])]
        df_esop = df_latest[df_latest["asset_class"] == "ESOP"]
        df_prop = df_latest[df_latest["asset_class"] == "Property"]
        df_veh = df_latest[df_latest["asset_class"] == "Vehicle"]
        df_liab = df_latest[df_latest["asset_class"] == "Liability"]

        b1_val = df_bank["value"].sum()
        b2_val = df_bonds["value"].sum()
        b3_val = df_equity["value"].sum()
        b4_raw = df_esop["value"].sum()
        b4_disc = round(b4_raw * (1 - haircut_pct / 100), 2)
        b5_val = df_prop["value"].sum()
        b6_val = df_veh["value"].sum()
        b7_val = df_liab["value"].sum()

        # USD vs INR split for Market Liquid (B3)
        _USD_SOURCES = {"IndMoney", "E*TRADE"}
        b3_usd = df_equity[df_equity["source"].isin(_USD_SOURCES)]["value"].sum()
        b3_inr = b3_val - b3_usd

        # Bond vs FD split for Near Liquid (B2)
        b2_bond = df_bonds[df_bonds["asset_class"] == "Bond"]["value"].sum()
        b2_fd = df_bonds[df_bonds["asset_class"] == "FD"]["value"].sum()

        # Progression metrics
        liquid_nw = b1_val + b2_val + b3_val - b7_val
        core_nw = liquid_nw + b5_val
        aspirational_nw = core_nw + b4_disc
        lifestyle_nw = aspirational_nw + b6_val

        # Net networth (respects vehicles toggle for pie / bucket display)
        total_networth = (
            b1_val + b2_val + b3_val + b4_disc + b5_val
            + (b6_val if include_vehicles else 0)
            - b7_val
        )

        # ---------------------------------------------------------------
        # Build bucket table rows
        # ---------------------------------------------------------------
        def _detail_b2():
            parts = []
            if b2_bond > 0:
                parts.append(f"Bonds {format_inr(b2_bond)}")
            if b2_fd > 0:
                parts.append(f"FDs {format_inr(b2_fd)}")
            return " · ".join(parts) if parts else "—"

        def _detail_b3():
            parts = []
            if b3_inr > 0:
                parts.append(f"INR {format_inr(b3_inr)}")
            if b3_usd > 0:
                parts.append(f"USD {format_inr(b3_usd)}")
            return " · ".join(parts) if parts else "—"

        bank_count = df_bank["name"].nunique()
        prop_count = len(df_prop)
        veh_count = len(df_veh)

        bucket_rows = []

        if b1_val > 0:
            bucket_rows.append({
                "Bucket": "🏦 Immediate Liquidity",
                "Value": b1_val,
                "Detail": f"{bank_count} account{'s' if bank_count != 1 else ''}",
            })
        if b2_val > 0:
            bucket_rows.append({
                "Bucket": "💰 Near Liquid",
                "Value": b2_val,
                "Detail": _detail_b2(),
            })
        if b3_val > 0:
            bucket_rows.append({
                "Bucket": "📈 Market Liquid",
                "Value": b3_val,
                "Detail": _detail_b3(),
            })
        if b4_raw > 0:
            bucket_rows.append({
                "Bucket": "🔒 Illiquid Equity",
                "Value": b4_disc,
                "Detail": f"Raw {format_inr(b4_raw)} · {haircut_pct}% haircut",
            })
        if b5_val > 0:
            bucket_rows.append({
                "Bucket": "🏠 Real Estate",
                "Value": b5_val,
                "Detail": f"{prop_count} {'property' if prop_count == 1 else 'properties'} (net of loan)",
            })
        if b6_val > 0:
            veh_label = "included" if include_vehicles else "excluded from total"
            bucket_rows.append({
                "Bucket": "🚗 Lifestyle Assets",
                "Value": b6_val,
                "Detail": f"{veh_count} vehicle{'s' if veh_count != 1 else ''} ({veh_label})",
            })
        if b7_val > 0:
            bucket_rows.append({
                "Bucket": "💳 Liabilities",
                "Value": -b7_val,
                "Detail": "Subtracted from total",
            })

        bucket_df = pd.DataFrame(bucket_rows)

        # ---------------------------------------------------------------
        # Progression metrics row
        # ---------------------------------------------------------------
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("💧 Liquid", format_inr(liquid_nw),
                      help="Bank + Near Liquid + Market Liquid − Liabilities")
        with m2:
            st.metric("🏗 Core", format_inr(core_nw),
                      help="Liquid + Real Estate")
        with m3:
            st.metric("🎯 Aspirational", format_inr(aspirational_nw),
                      help=f"Core + Illiquid Equity (after {haircut_pct}% haircut)")
        with m4:
            st.metric("✨ Lifestyle", format_inr(lifestyle_nw),
                      help="Aspirational + Lifestyle Assets (always full)")

        st.markdown("")

        # ---------------------------------------------------------------
        # Layout: bucket table | pie
        # ---------------------------------------------------------------
        col_tbl, col_pie = st.columns([1, 1])

        with col_tbl:
            if not bucket_df.empty:
                # Style liability row in red
                def _style_row(row):
                    if row["Bucket"].startswith("💳"):
                        return ["color: #cc3333; font-weight: bold"] * len(row)
                    return [""] * len(row)

                display_df = bucket_df.copy()
                display_df["Value"] = display_df["Value"].apply(
                    lambda v: f"({format_inr(abs(v))})" if v < 0 else format_inr(v)
                )
                styled = display_df.style.apply(_style_row, axis=1)
                st.dataframe(styled, use_container_width=True, hide_index=True)

        with col_pie:
            # Pie: positive buckets only; use discounted ESOP; respect vehicles toggle
            pie_rows = [r for r in bucket_rows if r["Value"] > 0]
            if not include_vehicles:
                pie_rows = [r for r in pie_rows if not r["Bucket"].startswith("🚗")]
            if pie_rows:
                pie_df = pd.DataFrame(pie_rows)
                fig_pie = px.pie(
                    pie_df,
                    values="Value",
                    names="Bucket",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig_pie.update_traces(
                    textinfo="percent+label",
                    hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>",
                )
                fig_pie.update_layout(showlegend=False, margin=dict(t=20, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")

        inner_bank, inner_equity, inner_bonds, inner_esop, inner_prop, inner_veh = st.tabs(["🏦 Bank Accounts", "📈 Equity", "🏛 Bonds & FDs", "🔒 ESOPs", "🏠 Property", "🚗 Vehicles"])

        # Reusable column_config entries
        _cc_inr = st.column_config.NumberColumn(format="₹%.0f")
        _cc_date = st.column_config.DateColumn(format="DD MMM YYYY")
        _cc_units = st.column_config.NumberColumn(format="%.4f")
        _cc_shares = st.column_config.NumberColumn(format="%.0f")

        # -------------------------------------------------------------------
        # Bank Accounts
        # -------------------------------------------------------------------
        with inner_bank:
            df_bank = df_latest[df_latest["asset_class"] == "Bank"].copy()
            if df_bank.empty:
                st.info("No bank account data found.")
            else:
                bank_by_source = (
                    df_bank.groupby("source")["value"]
                    .sum()
                    .reset_index()
                    .sort_values("value", ascending=False)
                )
                tbl = df_bank[["source", "value", "report_date"]].rename(
                    columns={"source": "Account", "value": "Balance", "report_date": "As of"}
                )
                if len(bank_by_source) > 1:
                    col_bc, col_bt = st.columns([2, 1])
                    with col_bc:
                        fig_bank = px.bar(
                            bank_by_source,
                            x="source",
                            y="value",
                            color="source",
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={"source": "Account", "value": "Balance (₹)"},
                        )
                        fig_bank.update_traces(
                            texttemplate="₹%{y:,.0f}",
                            textposition="outside",
                            hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                        )
                        fig_bank.update_layout(showlegend=False, margin=dict(t=20, b=0))
                        st.plotly_chart(fig_bank, use_container_width=True)
                    with col_bt:
                        st.dataframe(tbl, use_container_width=True, hide_index=True,
                                     column_config={"Balance": _cc_inr, "As of": _cc_date})
                else:
                    st.dataframe(tbl, use_container_width=True, hide_index=True,
                                 column_config={"Balance": _cc_inr, "As of": _cc_date})

        # -------------------------------------------------------------------
        # Equity
        # -------------------------------------------------------------------
        with inner_equity:
            df_eq = df_latest[df_latest["asset_class"].isin(["Stock", "Mutual Fund"])].copy()
            if df_eq.empty:
                st.info("No equity data found.")
            else:
                eq_by_source = (
                    df_eq.groupby(["source", "asset_class"])["value"]
                    .sum()
                    .reset_index()
                    .sort_values("value", ascending=False)
                )
                tbl_src = eq_by_source.rename(
                    columns={"source": "Source", "asset_class": "Type", "value": "Value"}
                )
                if eq_by_source["source"].nunique() > 1:
                    col_ec, col_et = st.columns([2, 1])
                    with col_ec:
                        fig_eq = px.bar(
                            eq_by_source,
                            x="source",
                            y="value",
                            color="asset_class",
                            barmode="stack",
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={"source": "Source", "value": "Value (₹)", "asset_class": "Type"},
                        )
                        fig_eq.update_traces(
                            hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                        )
                        fig_eq.update_layout(margin=dict(t=20, b=0))
                        st.plotly_chart(fig_eq, use_container_width=True)
                    with col_et:
                        st.dataframe(tbl_src, use_container_width=True, hide_index=True,
                                     column_config={"Value": _cc_inr})
                else:
                    st.dataframe(tbl_src, use_container_width=True, hide_index=True,
                                 column_config={"Value": _cc_inr})

                st.markdown("---")
                st.subheader("Holdings")
                df_eq_disp = df_eq.sort_values("value", ascending=False)[
                    ["asset_class", "source", "name", "units", "price", "value", "notes"]
                ].rename(columns={
                    "asset_class": "Type", "source": "Source", "name": "Name",
                    "units": "Units", "price": "Price", "value": "Value (₹)", "notes": "Notes",
                })
                st.dataframe(
                    df_eq_disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Value (₹)": _cc_inr,
                        "Price": _cc_inr,
                        "Units": _cc_units,
                    },
                )

        # -------------------------------------------------------------------
        # Bonds & FDs
        # -------------------------------------------------------------------
        with inner_bonds:
            df_bonds = df_latest[df_latest["asset_class"].isin(["Bond", "FD"])].copy()
            if df_bonds.empty:
                st.info("No bonds or FD data found.")
            else:
                bonds_by_source = (
                    df_bonds.groupby(["source", "asset_class"])["value"]
                    .sum()
                    .reset_index()
                    .sort_values("value", ascending=False)
                )
                tbl_b = bonds_by_source.rename(
                    columns={"source": "Source", "asset_class": "Type", "value": "Value"}
                )
                if bonds_by_source["source"].nunique() > 1:
                    col_bondc, col_bondt = st.columns([2, 1])
                    with col_bondc:
                        fig_bonds = px.bar(
                            bonds_by_source,
                            x="source",
                            y="value",
                            color="asset_class",
                            barmode="stack",
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={"source": "Source", "value": "Value (₹)", "asset_class": "Type"},
                        )
                        fig_bonds.update_traces(
                            hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                        )
                        fig_bonds.update_layout(margin=dict(t=20, b=0))
                        st.plotly_chart(fig_bonds, use_container_width=True)
                    with col_bondt:
                        st.dataframe(tbl_b, use_container_width=True, hide_index=True,
                                     column_config={"Value": _cc_inr})
                else:
                    st.dataframe(tbl_b, use_container_width=True, hide_index=True,
                                 column_config={"Value": _cc_inr})

                st.markdown("---")
                st.subheader("Holdings")
                df_bonds_disp = df_bonds.sort_values("value", ascending=False)[
                    ["asset_class", "source", "name", "value", "notes"]
                ].rename(columns={
                    "asset_class": "Type", "source": "Source", "name": "Name",
                    "value": "Value (₹)", "notes": "Notes",
                })
                st.dataframe(
                    df_bonds_disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Value (₹)": _cc_inr},
                )

        # -------------------------------------------------------------------
        # ESOPs
        # -------------------------------------------------------------------
        with inner_esop:
            df_esop = df_latest[df_latest["asset_class"] == "ESOP"].copy()
            if df_esop.empty:
                st.info("No ESOP data found. Add a Carta `exerciseHistory.csv` to `source_files/carta/`.")
            else:
                st.caption("Values are based on the last known Fair Market Value (FMV). ESOPs are illiquid — actual realisation depends on a liquidity event.")

                esop_by_source = (
                    df_esop.groupby("source")["value"]
                    .sum()
                    .reset_index()
                    .sort_values("value", ascending=False)
                )
                tbl_e = esop_by_source.rename(columns={"source": "Source", "value": "Value"})
                if len(esop_by_source) > 1:
                    col_ec, col_et = st.columns([2, 1])
                    with col_ec:
                        fig_esop = px.bar(
                            esop_by_source,
                            x="source",
                            y="value",
                            color="source",
                            color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={"source": "Source", "value": "Value (₹)"},
                        )
                        fig_esop.update_traces(
                            texttemplate="₹%{y:,.0f}",
                            textposition="outside",
                            hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
                        )
                        fig_esop.update_layout(showlegend=False, margin=dict(t=20, b=0))
                        st.plotly_chart(fig_esop, use_container_width=True)
                    with col_et:
                        st.dataframe(tbl_e, use_container_width=True, hide_index=True,
                                     column_config={"Value": _cc_inr})
                else:
                    st.dataframe(tbl_e, use_container_width=True, hide_index=True,
                                 column_config={"Value": _cc_inr})

                st.markdown("---")
                st.subheader("Holdings")
                df_esop_disp = df_esop.sort_values("value", ascending=False)[
                    ["source", "name", "units", "price", "value", "notes"]
                ].rename(columns={
                    "source": "Source", "name": "Company", "units": "Shares",
                    "price": "Price/Share (₹)", "value": "Value (₹)", "notes": "Notes",
                })
                st.dataframe(
                    df_esop_disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Value (₹)": _cc_inr,
                        "Price/Share (₹)": _cc_inr,
                        "Shares": _cc_shares,
                    },
                )

        # -------------------------------------------------------------------
        # Property
        # -------------------------------------------------------------------
        with inner_prop:
            df_prop = df_latest[df_latest["asset_class"] == "Property"].copy()
            if df_prop.empty:
                st.info("No property data found. Add `.txt` files to `source_files/property/`.")
            else:
                st.caption("Values are based on current market estimates. Update the .txt files in source_files/property/ to refresh valuations.")
                df_prop_disp = df_prop.sort_values("value", ascending=False)[
                    ["name", "value", "report_date", "notes"]
                ].rename(columns={
                    "name": "Property", "value": "Est. Value (₹)",
                    "report_date": "As of", "notes": "Notes",
                })
                st.dataframe(
                    df_prop_disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Est. Value (₹)": _cc_inr, "As of": _cc_date},
                )

        # -------------------------------------------------------------------
        # Vehicles
        # -------------------------------------------------------------------
        with inner_veh:
            df_veh = df_latest[df_latest["asset_class"] == "Vehicle"].copy()
            if df_veh.empty:
                st.info("No vehicle data found. Add `.txt` files to `source_files/vehicles/`.")
            else:
                st.caption("Values are estimated resale prices. Update `value` and `date` in each file to refresh.")
                df_veh_disp = df_veh.sort_values("value", ascending=False)[
                    ["name", "value", "report_date", "notes"]
                ].rename(columns={
                    "name": "Vehicle", "value": "Est. Resale Value (₹)",
                    "report_date": "As of", "notes": "Notes",
                })
                st.dataframe(
                    df_veh_disp,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Est. Resale Value (₹)": _cc_inr, "As of": _cc_date},
                )


# ===========================================================================
# TAB 2: Historical Trend
# ===========================================================================

with tab2:
    if df_all.empty:
        st.info("No holdings data found.")
    else:
        df_trend = (
            df_all.groupby("report_date")["value"]
            .sum()
            .reset_index()
            .sort_values("report_date")
        )

        if len(df_trend) < 2:
            st.info(
                "Only one data point found. Upload files with different dates to see a trend. "
                f"Current snapshot: {format_inr(df_trend['value'].iloc[0])} "
                f"as of {df_trend['report_date'].iloc[0].strftime('%d %b %Y')}."
            )
        else:
            fig_line = px.line(
                df_trend,
                x="report_date",
                y="value",
                markers=True,
                title="Total Networth Over Time",
                labels={"report_date": "Date", "value": "Networth (₹)"},
            )
            fig_line.update_traces(
                hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>",
                line=dict(width=2),
            )
            fig_line.update_yaxes(tickformat="₹,.0f")
            st.plotly_chart(fig_line, use_container_width=True)

        df_class_trend = (
            df_all.groupby(["report_date", "asset_class"])["value"]
            .sum()
            .reset_index()
            .sort_values("report_date")
        )

        if not df_class_trend.empty:
            fig_area = px.area(
                df_class_trend,
                x="report_date",
                y="value",
                color="asset_class",
                title="Networth by Asset Class Over Time",
                labels={"report_date": "Date", "value": "Value (₹)", "asset_class": "Asset Class"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_area.update_traces(
                hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>",
            )
            st.plotly_chart(fig_area, use_container_width=True)

        st.subheader("Networth by Date")
        df_table = df_trend.copy()
        df_table["report_date"] = df_table["report_date"].dt.strftime("%d %b %Y")
        df_table["value"] = df_table["value"].apply(format_inr)
        df_table = df_table.rename(columns={"report_date": "Date", "value": "Total Networth"})
        st.dataframe(df_table, use_container_width=True, hide_index=True)

