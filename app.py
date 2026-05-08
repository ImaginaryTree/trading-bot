"""
IDX Trading Bot Dashboard
─────────────────────────
Entry point. Run with:
    streamlit run app.py

Structure
    core/config.py           — constants
    core/data.py             — data fetching (yfinance)
    core/indicators.py       — technical indicator math
    core/signals.py          — signal generation & aggregation
    core/scalp_indicators.py — EMA/RSI-7/VWAP/Stoch/ATR for scalping
    core/scalp_signals.py    — scalp signal engine + historical scan
    core/quant_engine.py     — buy/sell volume decomposition + Monte Carlo
    ui/charts.py             — Plotly figure builders (swing)
    ui/scalp_charts.py       — Plotly figure builders (scalp)
    ui/quant_charts.py       — Plotly figure builders (quant)
    ui/watchlist.py          — watchlist tab renderer
    ui/analysis.py           — analysis tab renderer
    ui/scalping.py           — scalping tab renderer
    ui/quant.py              — quant dashboard tab renderer
    utils/formatting.py      — pure formatting helpers
"""

from __future__ import annotations

import time
from datetime import datetime

import pytz
import streamlit as st

from core.config import (
    DATA_INTERVALS,
    DATA_PERIODS,
    IDX_TIMEZONE,
    IDX_WATCHLIST,
    REFRESH_SECONDS,
)
from core.data import fetch_watchlist_quotes
from ui.analysis import render_analysis
from ui.quant import render_quant
from ui.scalping import render_scalping
from ui.watchlist import render_watchlist
from utils.formatting import market_status

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IDX Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal global CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 IDX Bot")
    st.caption("Indonesia Stock Exchange Dashboard")
    st.divider()

    # Market clock
    wib = pytz.timezone(IDX_TIMEZONE)
    now_wib = datetime.now(wib)
    status_label, _ = market_status(now_wib.hour)
    st.markdown(f"**{status_label}**")
    st.caption(f"🕐 {now_wib.strftime('%H:%M:%S WIB  %d %b %Y')}")
    st.divider()

    # Ticker picker
    selected_ticker = st.selectbox(
        "Select stock",
        options=list(IDX_WATCHLIST.keys()),
        format_func=lambda t: f"{t} — {IDX_WATCHLIST[t]}",
    )

    col_p, col_i = st.columns(2)
    selected_period   = col_p.selectbox("Period",   DATA_PERIODS,   index=1)
    selected_interval = col_i.selectbox("Interval", DATA_INTERVALS, index=2)

    st.divider()

    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto-refresh", value=True)
    refresh_secs = st.slider(
        "Refresh every (s)", 30, 300, REFRESH_SECONDS, step=30,
        disabled=not auto_refresh,
    )

    if st.button("🔄 Refresh now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Data via Yahoo Finance. Not financial advice.")


# ── Cached data loaders ───────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_watchlist_quotes() -> list[dict]:
    return fetch_watchlist_quotes()


# ── Main tabs ─────────────────────────────────────────────────────────────────
st.title("IDX Stock Trading Bot Dashboard")

tab_watch, tab_analysis, tab_scalp, tab_quant = st.tabs([
    "📋 Watchlist", "🔍 Analysis", "⚡ Scalping", "📊 Quant"
])

with tab_watch:
    quotes = load_watchlist_quotes()
    render_watchlist(quotes)

with tab_analysis:
    render_analysis(selected_ticker, selected_period, selected_interval)

with tab_scalp:
    render_scalping(selected_ticker)

with tab_quant:
    render_quant(selected_ticker)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    refresh_placeholder = st.empty()
    for remaining in range(refresh_secs, 0, -1):
        refresh_placeholder.caption(f"⏱ Next refresh in {remaining}s")
        time.sleep(1)
    st.cache_data.clear()
    st.rerun()