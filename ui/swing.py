"""
Swing Trade tab
───────────────
Full swing trade analysis dashboard with 6 strategies and a
confluence trade setup card.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import IDX_WATCHLIST, SWING_INTERVALS, SWING_PERIODS
from core.data import fetch_ohlcv
from core.swing_engine import run_swing_analysis
from ui.swing_charts import (
    confluence_radar,
    fibonacci_sr_chart,
    ichimoku_chart,
    supertrend_elder_chart,
)
from utils.formatting import signal_emoji

_VERDICT_CFG = {
    "BUY":  ("rgba(38,166,154,0.12)", "#26a69a", "🟢 BUY SETUP"),
    "SELL": ("rgba(239,83,80,0.12)",  "#ef5350", "🔴 SELL SETUP"),
    "WAIT": ("rgba(144,164,174,0.12)","#90A4AE", "⚪ WAIT — No confluence"),
}

_ACTION_COLOR = {"BUY": "#26a69a", "SELL": "#ef5350", "HOLD": "#ffc107"}
_ACTION_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}


def _trade_setup_card(result: dict) -> None:
    verdict = result["verdict"]
    bg, col, label = _VERDICT_CFG.get(verdict, _VERDICT_CFG["WAIT"])
    conf    = result["confidence"]
    price   = result["price"]

    st.markdown(f"""
    <div style="background:{bg}; border:1.5px solid {col};
                border-radius:14px; padding:20px 28px; margin-bottom:14px">
      <div style="display:flex; align-items:flex-start; gap:24px; flex-wrap:wrap">
        <div>
          <div style="font-size:1.7rem; font-weight:700; color:{col}">{label}</div>
          <div style="color:#aaa; font-size:0.85rem; margin-top:2px">
            Confluence: {result['buy_count'] if verdict=='BUY' else result['sell_count']}/6 strategies
            agree · Weighted score: {result['buy_score'] if verdict=='BUY' else result['sell_score']}
          </div>
        </div>
        <div style="margin-left:auto; display:flex; gap:32px; flex-wrap:wrap">
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">Entry</div>
            <div style="font-size:1.1rem;font-weight:600">Rp {price:,.0f}</div>
          </div>
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">Target 1</div>
            <div style="font-size:1.1rem;font-weight:600;color:{col}">Rp {result['target_1']:,.0f}
              <span style="font-size:0.8rem">(+{result['t1_pct']:.2f}%)</span></div>
          </div>
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">Target 2</div>
            <div style="font-size:1.1rem;font-weight:600;color:{col}">Rp {result['target_2']:,.0f}</div>
          </div>
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">Target 3</div>
            <div style="font-size:1.1rem;font-weight:600;color:{col}">Rp {result['target_3']:,.0f}</div>
          </div>
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">Stop Loss</div>
            <div style="font-size:1.1rem;font-weight:600;color:#ef5350">Rp {result['stop_loss']:,.0f}
              <span style="font-size:0.8rem">(-{result['sl_pct']:.2f}%)</span></div>
          </div>
          <div style="text-align:center">
            <div style="color:#aaa;font-size:0.75rem">R : R</div>
            <div style="font-size:1.1rem;font-weight:700;
              color:{'#26a69a' if result['risk_reward']>=2 else '#ffc107' if result['risk_reward']>=1 else '#ef5350'}">
              1 : {result['risk_reward']:.2f}</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _signal_breakdown_table(signals: dict) -> None:
    rows = []
    for name, sig in signals.items():
        action = sig["action"]
        em = _ACTION_EMOJI.get(action, "⚪")
        strength_dots = "●" * sig["strength"] + "○" * (3 - sig["strength"])
        rows.append({
            "Strategy":  name,
            "Signal":    f"{em} {action}",
            "Strength":  strength_dots,
            "Reason":    sig["reason"],
        })

    df = pd.DataFrame(rows)

    def _color_signal(col):
        if col.name != "Signal":
            return [""] * len(col)
        styles = []
        for v in col:
            if "BUY"  in v: styles.append("color:#26a69a;font-weight:600")
            elif "SELL" in v: styles.append("color:#ef5350;font-weight:600")
            else:             styles.append("color:#ffc107;font-weight:600")
        return styles

    st.dataframe(df.style.apply(_color_signal),
                 use_container_width=True, hide_index=True)


def render_swing(ticker: str) -> None:
    name = IDX_WATCHLIST.get(ticker, ticker)
    st.subheader(f"📈 Swing Trade Analysis — {ticker}  ·  {name}")

    # ── Parameters ────────────────────────────────────────────────────────────
    with st.expander("⚙️ Parameters", expanded=False):
        c1, c2 = st.columns(2)
        interval = c1.selectbox("Interval", SWING_INTERVALS, index=2, key="sw_int")
        period   = c2.selectbox("Period",   SWING_PERIODS,   index=1, key="sw_per")

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner(f"Running 6 swing strategies on {ticker}…"):
        raw = fetch_ohlcv(ticker, period=period, interval=interval)

    if raw.empty:
        st.error("No data returned. Try a different period or interval.")
        return
    if len(raw) < 55:
        st.warning(f"Only {len(raw)} bars — Ichimoku needs 52+ bars. Try a wider period.")

    result = run_swing_analysis(raw)
    df     = result["enriched_df"]

    # ── Trade setup card ──────────────────────────────────────────────────────
    _trade_setup_card(result)

    # ── Confluence radar + signal table ───────────────────────────────────────
    col_radar, col_table = st.columns([1, 2])
    with col_radar:
        fig_radar = confluence_radar(result["signals"])
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_table:
        st.markdown("**Strategy breakdown**")
        _signal_breakdown_table(result["signals"])

    st.divider()

    # ── Charts (3 tabs within the tab) ───────────────────────────────────────
    chart_tab1, chart_tab2, chart_tab3 = st.tabs([
        "🌥️ Ichimoku + MACD",
        "⚡ Supertrend + Elder",
        "📐 Fibonacci + S/R",
    ])

    with chart_tab1:
        st.caption(
            "**Ichimoku Cloud** — trade in the direction of the cloud. "
            "Green cloud = bullish, red cloud = bearish. "
            "Best entry: price pulling back to Kijun (purple) inside an uptrend."
        )
        fig_ichi = ichimoku_chart(df, result, ticker)
        st.plotly_chart(fig_ichi, use_container_width=True)

    with chart_tab2:
        st.caption(
            "**Supertrend** — the line flips sides when trend reverses. "
            "Use it as a trailing stop on swing trades. "
            "**Elder Triple Screen** — tide (EMA slope) must agree with wave (Stoch pullback)."
        )
        fig_st = supertrend_elder_chart(df, result, ticker)
        st.plotly_chart(fig_st, use_container_width=True)

    with chart_tab3:
        st.caption(
            "**Fibonacci** — key retracement levels from the most recent swing high/low. "
            "38.2%, 50%, 61.8% are the classic entry zones in a trending market. "
            "**S/R** — broken resistance becomes support, vice versa."
        )
        fig_fib = fibonacci_sr_chart(df, result, ticker)
        st.plotly_chart(fig_fib, use_container_width=True)

    st.divider()

    # ── Key stats ─────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("ATR",          f"Rp {result['atr']:,.0f}")
    m2.metric("ATR / Price",  f"{result['atr']/result['price']*100:.2f}%")
    m3.metric("Risk : Reward", f"1 : {result['risk_reward']:.2f}",
              "✅ Good" if result['risk_reward'] >= 2 else "⚠️ Tight")
    m4.metric("Round-trip cost", f"{result['cost_pct']:.3f}%")
    m5.metric("Net T1 edge",
              f"{result['t1_pct'] - result['cost_pct']:+.2f}%",
              delta_color="normal" if result['t1_pct'] > result['cost_pct'] else "inverse")

    # ── Fibonacci detail ──────────────────────────────────────────────────────
    with st.expander("📐 Fibonacci levels detail"):
        fib = result["fib"]
        st.markdown(f"**Swing High**: Rp {fib['swing_high']:,.0f}  |  "
                    f"**Swing Low**: Rp {fib['swing_low']:,.0f}  |  "
                    f"**Trend**: {fib['trend']}")
        rows = [(k.replace("fib_", ""), f"Rp {v:,.0f}") for k, v in fib["levels"].items()]
        st.dataframe(pd.DataFrame(rows, columns=["Level", "Price"]),
                     use_container_width=True, hide_index=True)

    # ── S/R levels ────────────────────────────────────────────────────────────
    with st.expander("📊 Support / Resistance levels"):
        sr = result["sr"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Resistance**")
            for r in (sr["resistance_levels"] or []):
                st.markdown(f"- Rp {r:,.0f}")
        with c2:
            st.markdown("**Support**")
            for s in (sr["support_levels"] or []):
                st.markdown(f"- Rp {s:,.0f}")
        st.caption(f"Volume surge on last bar: {sr['vol_surge']:.2f}× average")

    # ── Strategy explainer ────────────────────────────────────────────────────
    with st.expander("📖 How each strategy works"):
        st.markdown("""
**1. Ichimoku Cloud (一目均衡表)**
The most complete single-indicator swing system. Developed in Japan —
very relevant for IDX as it's widely followed by Asian institutional traders.
The cloud (Kumo) shows support/resistance zones. Trade above it for longs,
below for shorts. The Tenkan/Kijun cross confirms entries. Strongest when
price, cloud colour, and TK cross all agree.

**2. Supertrend**
An ATR-based trailing stop line. When it flips from above to below price,
that's the buy signal — and it becomes your stop as the trade runs.
Clean, rules-based, and excellent for swing trades lasting days to weeks.
ATR multiplier = 3.0 (standard setting).

**3. Fibonacci Retracement**
After a significant move, price almost always retraces before continuing.
The 38.2%, 50%, and 61.8% levels are where swing traders look for reversals.
Only trade WITH the trend — use Fibonacci to find the dip to buy, not to
predict a reversal.

**4. MACD Divergence**
Regular MACD crossovers lag badly on swing timeframes. Divergence (price
making a new low while MACD makes a higher low) is much more powerful —
it signals a shift in momentum BEFORE the price reversal happens.

**5. Elder Triple Screen (Dr. Alexander Elder)**
Three timeframes must agree before entering:
- Screen 1: Weekly EMA slope (is the tide in or out?)
- Screen 2: Daily stochastic pulls back against the tide (wave pullback)
- Screen 3: Intraday/daily breakout in the trend direction (ripple entry)
Very effective because it forces discipline — no trading against the tide.

**6. Support / Resistance Breakout**
Old-school but reliable. Key S/R levels come from previous swing highs/lows.
A breakout above resistance on 1.5× average volume is institutional confirmation.
Without volume, breakouts are often fakeouts.
        """)

    st.caption(
        "⚠️ Swing signals are generated from OHLCV data only. "
        "Confluence of 3+ strategies is required for a high-confidence trade setup. "
        "Always manage risk with a defined stop-loss. Not financial advice."
    )
