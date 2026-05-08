"""
Watchlist tab: renders the overview of all tracked IDX stocks.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.charts import watchlist_bar_chart
from utils.formatting import format_change, format_idr, signal_emoji


def render_watchlist(quotes: list[dict]) -> None:
    if not quotes:
        st.warning("No quote data available. Check your connection.")
        return

    st.subheader("📊 IDX Watchlist")

    # Summary metrics row
    gainers  = sum(1 for q in quotes if q["change_pct"] > 0)
    losers   = sum(1 for q in quotes if q["change_pct"] < 0)
    flat     = len(quotes) - gainers - losers
    avg_chg  = sum(q["change_pct"] for q in quotes) / len(quotes)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Gainers", gainers)
    c2.metric("🔴 Losers",  losers)
    c3.metric("⚪ Flat",    flat)
    c4.metric("Avg change", f"{avg_chg:+.2f}%")

    # Bar chart
    st.plotly_chart(watchlist_bar_chart(quotes), use_container_width=True)

    # Detailed table
    rows = []
    for q in quotes:
        direction = "▲" if q["change_pct"] >= 0 else "▼"
        rows.append({
            "Ticker":     q["ticker"],
            "Name":       q["name"],
            "Price (IDR)": f"Rp {q['last_price']:,.0f}",
            "Change":     f"{direction} {abs(q['change_pct']):.2f}%",
            "Prev close": f"Rp {q['prev_close']:,.0f}",
            "Mkt cap":    format_idr(q["market_cap"]),
        })

    df = pd.DataFrame(rows)

    def highlight_change(col):
        if col.name != "Change":
            return [""] * len(col)
        return [
            "color: #26a69a" if "▲" in v else "color: #ef5350"
            for v in col
        ]

    st.dataframe(
        df.style.apply(highlight_change),
        use_container_width=True,
        hide_index=True,
    )
