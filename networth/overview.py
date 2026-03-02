"""
Networth Overview — controls, progression metrics, bucket breakdown, and historical trend.
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

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Loading holdings..."):
    df_all, load_errors = get_networth_data()

st.title("📊 Networth")

if load_errors:
    with st.expander(f"⚠️ {len(load_errors)} parse error(s)"):
        for e in load_errors:
            st.warning(e)

sum_tab, trend_tab = st.tabs(["Summary", "Historical Trend"])

# ===========================================================================
# Summary tab
# ===========================================================================

with sum_tab:
    if df_all.empty:
        st.info("No holdings data found. Add files to `source_files/` subfolders.")
        st.stop()

    # Latest snapshot per source
    latest_dates = df_all.groupby("source")["report_date"].max()
    df_latest = df_all[
        df_all.apply(lambda r: r["report_date"] == latest_dates[r["source"]], axis=1)
    ].copy()

    # ---------------------------------------------------------------
    # Controls
    # ---------------------------------------------------------------
    ctrl1, ctrl2, _ = st.columns([1, 1, 2])
    with ctrl1:
        haircut_pct = st.slider(
            "ESOP Haircut", 0, 80, 30, 5, format="%d%%",
            help="Discount applied to illiquid ESOP valuations",
        )
    with ctrl2:
        include_vehicles = st.checkbox(
            "Include Lifestyle Assets in total", value=False,
            help="Vehicles are depreciating assets — toggle to include in networth",
        )

    # ---------------------------------------------------------------
    # Bucket raw values
    # ---------------------------------------------------------------
    df_bank  = df_latest[df_latest["asset_class"] == "Bank"]
    df_eq    = df_latest[df_latest["asset_class"].isin(["Stock", "Mutual Fund"])]
    df_bonds = df_latest[df_latest["asset_class"].isin(["Bond", "FD"])]
    df_esop  = df_latest[df_latest["asset_class"] == "ESOP"]
    df_prop  = df_latest[df_latest["asset_class"] == "Property"]
    df_veh   = df_latest[df_latest["asset_class"] == "Vehicle"]
    df_liab  = df_latest[df_latest["asset_class"] == "Liability"]

    b1 = df_bank["value"].sum()
    b2 = df_bonds["value"].sum()
    b3 = df_eq["value"].sum()
    b4_raw  = df_esop["value"].sum()
    b4_disc = round(b4_raw * (1 - haircut_pct / 100), 2)
    b5 = df_prop["value"].sum()
    b6 = df_veh["value"].sum()
    b7 = df_liab["value"].sum()

    _USD = {"IndMoney", "E*TRADE"}
    b3_usd = df_eq[df_eq["source"].isin(_USD)]["value"].sum()
    b3_inr = b3 - b3_usd
    b2_bond = df_bonds[df_bonds["asset_class"] == "Bond"]["value"].sum()
    b2_fd   = df_bonds[df_bonds["asset_class"] == "FD"]["value"].sum()

    # ---------------------------------------------------------------
    # Progression metrics
    # ---------------------------------------------------------------
    liquid_nw       = b1 + b2 + b3 - b7
    core_nw         = liquid_nw + b5
    aspirational_nw = core_nw + b4_disc
    lifestyle_nw    = aspirational_nw + b6

    total_networth = (
        b1 + b2 + b3 + b4_disc + b5
        + (b6 if include_vehicles else 0)
        - b7
    )

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
    # Bucket rows
    # ---------------------------------------------------------------
    def _b2_detail():
        parts = []
        if b2_bond > 0: parts.append(f"Bonds {format_inr(b2_bond)}")
        if b2_fd   > 0: parts.append(f"FDs {format_inr(b2_fd)}")
        return " · ".join(parts) if parts else "—"

    def _b3_detail():
        parts = []
        if b3_inr > 0: parts.append(f"INR {format_inr(b3_inr)}")
        if b3_usd > 0: parts.append(f"USD {format_inr(b3_usd)}")
        return " · ".join(parts) if parts else "—"

    bank_count = df_bank["name"].nunique()
    prop_count = len(df_prop)
    veh_count  = len(df_veh)

    bucket_rows = []
    if b1 > 0:
        bucket_rows.append({"Bucket": "🏦 Immediate Liquidity", "Value": b1,
                            "Detail": f"{bank_count} account{'s' if bank_count != 1 else ''}"})
    if b2 > 0:
        bucket_rows.append({"Bucket": "💰 Near Liquid", "Value": b2, "Detail": _b2_detail()})
    if b3 > 0:
        bucket_rows.append({"Bucket": "📈 Market Liquid", "Value": b3, "Detail": _b3_detail()})
    if b4_raw > 0:
        bucket_rows.append({"Bucket": "🔒 Illiquid Equity", "Value": b4_disc,
                            "Detail": f"Raw {format_inr(b4_raw)} · {haircut_pct}% haircut"})
    if b5 > 0:
        bucket_rows.append({"Bucket": "🏠 Real Estate", "Value": b5,
                            "Detail": f"{prop_count} {'property' if prop_count == 1 else 'properties'} (net of loan)"})
    if b6 > 0:
        veh_label = "included" if include_vehicles else "excluded from total"
        bucket_rows.append({"Bucket": "🚗 Lifestyle Assets", "Value": b6,
                            "Detail": f"{veh_count} vehicle{'s' if veh_count != 1 else ''} ({veh_label})"})
    if b7 > 0:
        bucket_rows.append({"Bucket": "💳 Liabilities", "Value": -b7,
                            "Detail": "Subtracted from total"})

    bucket_df = pd.DataFrame(bucket_rows)

    # ---------------------------------------------------------------
    # Layout: bucket table | pie
    # ---------------------------------------------------------------
    col_tbl, col_pie = st.columns([1, 1])

    with col_tbl:
        st.metric("Net Networth", format_inr(total_networth))
        st.markdown("")
        if not bucket_df.empty:
            def _style_row(row):
                if row["Bucket"].startswith("💳"):
                    return ["color: #cc3333; font-weight: bold"] * len(row)
                return [""] * len(row)

            display_df = bucket_df.copy()
            display_df["Value"] = display_df["Value"].apply(
                lambda v: f"({format_inr(abs(v))})" if v < 0 else format_inr(v)
            )
            st.dataframe(
                display_df.style.apply(_style_row, axis=1),
                use_container_width=True,
                hide_index=True,
            )

    with col_pie:
        pie_rows = [r for r in bucket_rows if r["Value"] > 0]
        if not include_vehicles:
            pie_rows = [r for r in pie_rows if not r["Bucket"].startswith("🚗")]
        if pie_rows:
            pie_df = pd.DataFrame(pie_rows)
            fig = px.pie(
                pie_df, values="Value", names="Bucket", hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(
                textinfo="percent+label",
                hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>",
            )
            fig.update_layout(showlegend=False, margin=dict(t=20, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# Historical Trend tab
# ===========================================================================

with trend_tab:
    if df_all.empty:
        st.info("No holdings data found.")
    else:
        df_trend = (
            df_all.groupby("report_date")["value"]
            .sum().reset_index().sort_values("report_date")
        )

        if len(df_trend) < 2:
            st.info(
                "Only one data point found. Upload files with different dates to see a trend. "
                f"Current snapshot: {format_inr(df_trend['value'].iloc[0])} "
                f"as of {df_trend['report_date'].iloc[0].strftime('%d %b %Y')}."
            )
        else:
            fig_line = px.line(
                df_trend, x="report_date", y="value", markers=True,
                title="Total Networth Over Time",
                labels={"report_date": "Date", "value": "Networth (₹)"},
            )
            fig_line.update_traces(
                hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>",
                line=dict(width=2),
            )
            st.plotly_chart(fig_line, use_container_width=True)

        df_class_trend = (
            df_all.groupby(["report_date", "asset_class"])["value"]
            .sum().reset_index().sort_values("report_date")
        )
        if not df_class_trend.empty:
            fig_area = px.area(
                df_class_trend, x="report_date", y="value", color="asset_class",
                title="Networth by Asset Class Over Time",
                labels={"report_date": "Date", "value": "Value (₹)", "asset_class": "Asset Class"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_area.update_traces(hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>")
            st.plotly_chart(fig_area, use_container_width=True)

        st.subheader("Networth by Date")
        df_tbl = df_trend.rename(columns={"report_date": "Date", "value": "Total Networth"})
        st.dataframe(
            df_tbl,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn(format="DD MMM YYYY"),
                "Total Networth": st.column_config.NumberColumn(format="₹%.0f"),
            },
        )
