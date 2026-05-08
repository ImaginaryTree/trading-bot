"""
Quant Dashboard tab
────────────────────
Renders the full quantitative analytics dashboard in Streamlit.

Sections
  ① Data note & parameters
  ② Live flow metrics (auto-refreshes every 60s)
  ③ Buy/sell volume decomposition chart (4 panels)
  ④ Flow imbalance gauge + summary table
  ⑤ Monte Carlo fan chart
  ⑥ Return distribution histogram
  ⑦ Monte Carlo stats panel
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytz
import streamlit as st

from core.config import (
    IDX_TIMEZONE,
    IDX_WATCHLIST,
    MC_HORIZON_BARS,
    MC_SIMULATIONS,
    QUANT_INTERVALS,
    QUANT_PERIODS,
)
from core.data import fetch_ohlcv
from core.quant_engine import (
    decompose_volume,
    flow_summary,
    mc_signal,
    run_monte_carlo,
)
from ui.quant_charts import (
    buy_sell_volume_chart,
    flow_imbalance_gauge,
    mc_return_distribution,
    monte_carlo_chart,
)
from utils.formatting import format_idr, signal_emoji


# ── Helpers ───────────────────────────────────────────────────────────────────

def _direction_badge(direction: str, label: str = "") -> str:
    cfg = {
        "BULLISH": ("rgba(38,166,154,0.15)", "#26a69a", "🟢"),
        "BEARISH": ("rgba(239,83,80,0.15)",  "#ef5350", "🔴"),
        "NEUTRAL": ("rgba(255,193,7,0.12)",  "#ffc107", "🟡"),
        "BUY":     ("rgba(38,166,154,0.15)", "#26a69a", "🟢"),
        "SELL":    ("rgba(239,83,80,0.15)",  "#ef5350", "🔴"),
        "NEUTRAL_FLOW": ("rgba(144,164,174,0.12)", "#90A4AE", "⚪"),
    }
    bg, col, em = cfg.get(direction, cfg["NEUTRAL"])
    text = label or direction
    return (
        f'<span style="background:{bg}; border:1px solid {col}; color:{col}; '
        f'border-radius:8px; padding:4px 12px; font-weight:700; font-size:1rem">'
        f'{em} {text}</span>'
    )


def _fmt_vol(v: int) -> str:
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.1f}K"
    return str(v)


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_quant(ticker: str) -> None:
    name = IDX_WATCHLIST.get(ticker, ticker)
    st.subheader(f"📊 Quant Dashboard — {ticker}  ·  {name}")

    # ── Data note ─────────────────────────────────────────────────────────────
    wib     = pytz.timezone(IDX_TIMEZONE)
    now_wib = datetime.now(wib)
    st.info(
        f"**Data source**: Yahoo Finance 1-min OHLCV bars, refreshed every 60 s.  "
        f"Buy/sell volume is **inferred** via Tick Rule + BVC + candle body ratio  "
        f"(3-method blend). True Level-2 order book is not available via yfinance.  "
        f"Last update: **{now_wib.strftime('%H:%M:%S WIB')}**",
        icon="ℹ️",
    )

    # ── Parameters ───────────────────────────────────────────────────────────
    with st.expander("⚙️ Parameters", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        interval = c1.selectbox("Interval",   QUANT_INTERVALS, index=0, key="q_int")
        period   = c2.selectbox("Period",     QUANT_PERIODS,   index=0, key="q_per")
        n_sims   = c3.number_input("MC simulations", 100, 2000, MC_SIMULATIONS,
                                    step=100, key="q_sims")
        horizon  = c4.number_input("MC horizon (bars)", 5, 120, MC_HORIZON_BARS,
                                    step=5, key="q_horizon")

    # ── Fetch + enrich ────────────────────────────────────────────────────────
    with st.spinner(f"Loading {ticker} ({interval}) and running quant analysis…"):
        raw_df = fetch_ohlcv(ticker, period=period, interval=interval)

    if raw_df.empty:
        st.error("No data. For 1m interval use period '1d' or '5d'.")
        return

    df = decompose_volume(raw_df)
    fs = flow_summary(df)
    mc = run_monte_carlo(df, n_sims=int(n_sims), horizon=int(horizon))
    mc_dir, mc_reason = mc_signal(mc)

    # ── Top metrics bar ───────────────────────────────────────────────────────
    last_price  = float(df["Close"].iloc[-1])
    prev_price  = float(df["Close"].iloc[-2]) if len(df) > 1 else last_price
    price_delta = last_price - prev_price

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Price",       f"Rp {last_price:,.0f}",
              f"{price_delta:+.0f} ({price_delta/prev_price*100:+.2f}%)")
    m2.metric("Buy vol",     _fmt_vol(fs["total_buy_vol"]))
    m3.metric("Sell vol",    _fmt_vol(fs["total_sell_vol"]))
    m4.metric("Cum. delta",  _fmt_vol(abs(fs["cum_delta_final"])),
              "net buy" if fs["cum_delta_final"] >= 0 else "net sell",
              delta_color="normal" if fs["cum_delta_final"] >= 0 else "inverse")
    m5.metric("Flow imbal.", f"{fs['imbalance']*100:.1f}% buy")
    m6.metric("Bars loaded", str(len(df)))

    # ── Signal row ────────────────────────────────────────────────────────────
    flow_dir = fs["dominant_side"]
    col_flow, col_mc = st.columns(2)
    with col_flow:
        st.markdown("**Order flow signal**")
        st.markdown(_direction_badge(flow_dir, f"Flow: {flow_dir}"), unsafe_allow_html=True)
        imb = fs["imbalance"]
        st.caption(
            f"{imb*100:.1f}% of volume is buy-initiated — "
            f"{'strong buying pressure' if imb >= 0.65 else 'strong selling pressure' if imb <= 0.35 else 'balanced flow'}"
        )
    with col_mc:
        st.markdown("**Monte Carlo signal**")
        st.markdown(_direction_badge(mc_dir), unsafe_allow_html=True)
        st.caption(mc_reason)

    st.divider()

    # ── Volume decomposition chart ────────────────────────────────────────────
    st.markdown("### 📈 Buy / Sell Volume Decomposition")
    st.caption(
        "Green bars = estimated buy volume (buyer-initiated). "
        "Red bars = estimated sell volume. "
        "Net delta = buy − sell per bar. "
        "Cumulative delta = running order flow trend."
    )
    fig_vol = buy_sell_volume_chart(df, ticker)
    st.plotly_chart(fig_vol, use_container_width=True)

    # ── Flow imbalance gauge + detail table ──────────────────────────────────
    col_gauge, col_table = st.columns([1, 2])
    with col_gauge:
        fig_gauge = flow_imbalance_gauge(fs["imbalance"])
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_table:
        st.markdown("**Flow breakdown**")
        rows = [
            ("Total buy volume",   _fmt_vol(fs["total_buy_vol"])),
            ("Total sell volume",  _fmt_vol(fs["total_sell_vol"])),
            ("Net cumulative delta", _fmt_vol(abs(fs["cum_delta_final"])) +
             (" ▲ net buyers" if fs["cum_delta_final"] >= 0 else " ▼ net sellers")),
            ("Recent 5-bar delta", _fmt_vol(abs(fs["recent_delta"])) +
             (" buying" if fs["recent_delta"] >= 0 else " selling")),
            ("Dominant side",       fs["dominant_side"]),
            ("Current pressure",    fs["pressure"]),
            ("Inference method",    "Tick Rule + BVC + Candle body (blended)"),
        ]
        tbl = pd.DataFrame(rows, columns=["Metric", "Value"])
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    st.divider()

    # ── Monte Carlo fan chart ─────────────────────────────────────────────────
    st.markdown("### 🎲 Monte Carlo Price Simulation")
    st.caption(
        f"{int(n_sims):,} paths · {int(horizon)}-bar horizon · "
        "GBM with Student-t shocks (fat tails) · drift & vol estimated from this ticker's history"
    )

    if mc:
        fig_mc = monte_carlo_chart(mc, ticker)
        st.plotly_chart(fig_mc, use_container_width=True)

        # Stats panel
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Prob(price up)",     f"{mc['prob_up']:.1%}")
        s2.metric("Expected return",    f"{mc['expected_return']:+.3f}%")
        s3.metric("VaR 95%",            f"{mc['var_95']:+.3f}%",
                  help="Worst expected loss in 95% of scenarios")
        s4.metric("Best case (95th)",   f"{mc['best_case']:+.3f}%")
        s5.metric("Est. σ / bar",       f"{mc['sigma_per_bar']:.3f}%")

        # Return distribution
        st.markdown("**Terminal return distribution**")
        fig_dist = mc_return_distribution(mc)
        st.plotly_chart(fig_dist, use_container_width=True)

        # Interpretation
        cost = mc["cost_pct"]
        exp  = mc["expected_return"]
        with st.expander("📖 How to read this"):
            st.markdown(f"""
**Monte Carlo fan chart**
- Each faint line is one simulated price path over the next **{int(horizon)} bars**
- The **teal/green shaded band** is the 50th–75th percentile (likely upside)
- The **red shaded band** is the 5th–25th percentile (downside risk)
- The **white median line** is the 50th percentile — most likely single path
- The **dashed horizontal line** is today's price — above = profit, below = loss

**Return distribution**
- X-axis = terminal return % vs today's price
- Green bars = profitable outcomes, Red bars = loss outcomes
- **VaR 95%** = in 95% of simulations, your loss won't exceed this number
- **Expected return** = probability-weighted average across all paths

**Important**: Round-trip trading costs for IDX are approx. **{cost:.3f}%**
(0.1% sell tax + 0.15% × 2 broker commission). The expected return must
exceed this for a trade to be net positive in expectation.
            """)
    else:
        st.warning("Monte Carlo needs at least 10 bars of history.")

    st.caption("⚠️ Simulation uses historical volatility — past vol ≠ future vol. Not financial advice.")
