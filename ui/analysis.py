"""
Analysis tab: per-ticker deep-dive with chart and signal panel.
"""

from __future__ import annotations

import streamlit as st

from core.data import fetch_ohlcv
from core.indicators import add_all_indicators
from core.signals import aggregate_signals
from ui.charts import candlestick_with_indicators
from utils.formatting import signal_color, signal_emoji


def render_analysis(ticker: str, period: str, interval: str) -> None:
    st.subheader(f"🔍 Analysis — {ticker}")

    with st.spinner(f"Loading {ticker} data..."):
        df = fetch_ohlcv(ticker, period=period, interval=interval)

    if df.empty:
        st.error(f"Could not load data for {ticker}. Try a different period/interval.")
        return

    df = add_all_indicators(df)

    # ── Signal panel ──────────────────────────────────────────────
    agg = aggregate_signals(df)
    rec = agg["recommendation"]
    conf = agg["confidence"]

    col_signal, col_conf = st.columns([1, 2])
    with col_signal:
        color = signal_color(rec)
        st.markdown(
            f"""
            <div style="
                background: {'rgba(38,166,154,0.15)' if rec=='BUY' else 'rgba(239,83,80,0.15)' if rec=='SELL' else 'rgba(255,193,7,0.15)'};
                border: 1px solid {'#26a69a' if rec=='BUY' else '#ef5350' if rec=='SELL' else '#ffc107'};
                border-radius: 12px; padding: 20px; text-align: center;">
                <div style="font-size: 2.5rem;">{signal_emoji(rec)}</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: {'#26a69a' if rec=='BUY' else '#ef5350' if rec=='SELL' else '#ffc107'}">
                    {rec}
                </div>
                <div style="color: #aaa; font-size: 0.85rem">Confidence: {conf:.0%}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_conf:
        st.markdown("**Signal breakdown**")
        for name, result in agg["breakdown"].items():
            s = result["signal"]
            em = signal_emoji(s)
            reason = result["reasons"][0] if result["reasons"] else ""
            st.markdown(f"- **{name}**: {em} {s} — _{reason}_")

    st.divider()

    # ── Latest indicator values ────────────────────────────────────
    last = df.iloc[-1]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Close",    f"Rp {last['Close']:,.0f}")
    m2.metric("SMA 20",   f"Rp {last.get('SMA_20', 0):,.0f}" if "SMA_20" in df.columns else "—")
    m3.metric("SMA 50",   f"Rp {last.get('SMA_50', 0):,.0f}" if "SMA_50" in df.columns else "—")
    m4.metric("RSI",      f"{last.get('RSI', 0):.1f}"         if "RSI"   in df.columns else "—")
    m5.metric("MACD",     f"{last.get('MACD', 0):.4f}"        if "MACD"  in df.columns else "—")

    # ── Chart ──────────────────────────────────────────────────────
    fig = candlestick_with_indicators(df, ticker)
    st.plotly_chart(fig, use_container_width=True)

    # ── Raw data toggle ────────────────────────────────────────────
    with st.expander("📋 Raw OHLCV data"):
        st.dataframe(df.tail(50).iloc[::-1], use_container_width=True)
