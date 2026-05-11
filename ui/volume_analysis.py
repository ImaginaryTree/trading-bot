"""
Volume Analysis tab — Smart Money Detection
─────────────────────────────────────────────
Renders the full smart money / institutional footprint dashboard.

Sections
  ① Verdict card (ACCUMULATION / DISTRIBUTION / UNCLEAR)
  ② 5-method metric row
  ③ Main chart: price + Wyckoff phase + Smart Score + VPIN
  ④ Volume Profile
  ⑤ Effort vs Result scatter
  ⑥ CMF + OBV divergence
  ⑦ Wyckoff phase distribution
  ⑧ Method explainer
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import (
    IDX_WATCHLIST,
    VOL_ANALYSIS_INTERVALS,
    VOL_ANALYSIS_PERIODS,
)
from core.data import fetch_ohlcv
from core.volume_analysis import run_volume_analysis
from ui.volume_charts import (
    cmf_obv_chart,
    effort_vs_result_chart,
    smart_money_overview_chart,
    volume_profile_chart,
    wyckoff_phase_timeline,
)

_VERDICT_STYLE = {
    "ACCUMULATION": ("rgba(38,166,154,0.12)", "#26a69a", "🟢", "Smart money appears to be BUYING quietly"),
    "DISTRIBUTION": ("rgba(239,83,80,0.12)",  "#ef5350", "🔴", "Smart money appears to be SELLING quietly"),
    "UNCLEAR":      ("rgba(144,164,174,0.12)","#90A4AE", "⚪", "No clear institutional footprint detected"),
}

_PHASE_EMOJI = {
    "ACCUMULATION": "🟢", "MARKUP": "📈", "DISTRIBUTION": "🔴",
    "MARKDOWN": "📉", "SPRING": "💧", "UTAD": "⚠️", "UNCLEAR": "⚪",
}


def _verdict_card(summary: dict) -> None:
    verdict = summary["verdict"]
    bg, col, em, tagline = _VERDICT_STYLE.get(verdict, _VERDICT_STYLE["UNCLEAR"])
    score = summary["smart_score"]
    score_bar_pct = int((score + 1) / 2 * 100)   # map [-1,1] → [0,100]%

    st.markdown(f"""
    <div style="background:{bg}; border:1.5px solid {col};
                border-radius:14px; padding:22px 28px; margin-bottom:14px">
      <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap">
        <div style="font-size:2.8rem">{em}</div>
        <div>
          <div style="font-size:1.9rem; font-weight:700; color:{col}">{verdict}</div>
          <div style="color:#ccc; font-size:0.9rem">{tagline}</div>
        </div>
        <div style="margin-left:auto; text-align:right">
          <div style="color:#aaa; font-size:0.8rem">Smart Money Score</div>
          <div style="font-size:1.5rem; font-weight:700; color:{col}">{score:+.2f}</div>
          <div style="background:rgba(128,128,128,0.2); border-radius:4px; height:6px; width:120px; margin-top:4px">
            <div style="background:{col}; width:{score_bar_pct}%; height:6px; border-radius:4px"></div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _method_metrics(summary: dict) -> None:
    """5-column row — one metric per method."""
    c1, c2, c3, c4, c5 = st.columns(5)

    # VPIN
    vpin = summary["vpin"]
    vpin_label = "🔴 Informed" if vpin > 0.7 else "🟡 Mixed" if vpin > 0.5 else "🟢 Retail noise"
    c1.metric("VPIN", f"{vpin:.3f}", vpin_label)

    # Wyckoff
    phase = summary["wyckoff_phase"]
    c2.metric("Wyckoff phase", f"{_PHASE_EMOJI.get(phase,'')} {phase}")

    # EVR
    evr = summary["evr_signal"].replace("_", " ").title()
    c3.metric("Effort vs Result", evr)

    # CMF
    cmf = summary["cmf"]
    cmf_dir = "▲ Buying" if cmf > 0.05 else "▼ Selling" if cmf < -0.05 else "— Neutral"
    c4.metric("CMF", f"{cmf:+.3f}", cmf_dir)

    # OBV divergence
    obv = summary["obv_divergence"]
    obv_label = "🟢 Bullish div" if obv == "BULLISH_DIV" else "🔴 Bearish div" if obv == "BEARISH_DIV" else "None"
    c5.metric("OBV divergence", obv_label)


def _volume_profile_sidebar(summary: dict) -> None:
    st.markdown("**Volume Profile levels**")
    rows = [
        ("Point of Control (POC)", f"Rp {summary['poc']:,.0f}"),
        ("Value Area High",        f"Rp {summary['value_area_high']:,.0f}"),
        ("Value Area Low",         f"Rp {summary['value_area_low']:,.0f}"),
        ("Absorption bars",        str(summary["absorption_bars"])),
        ("Dominant phase",         summary["dominant_phase"]),
    ]
    st.dataframe(
        pd.DataFrame(rows, columns=["Level", "Value"]),
        use_container_width=True, hide_index=True,
    )


def render_volume_analysis(ticker: str) -> None:
    name = IDX_WATCHLIST.get(ticker, ticker)
    st.subheader(f"🧠 Smart Money / Volume Analysis — {ticker}  ·  {name}")

    # ── Parameters ────────────────────────────────────────────────────────────
    with st.expander("⚙️ Parameters", expanded=False):
        c1, c2 = st.columns(2)
        interval = c1.selectbox("Interval", VOL_ANALYSIS_INTERVALS, index=2, key="va_int")
        period   = c2.selectbox("Period",   VOL_ANALYSIS_PERIODS,   index=2, key="va_per")

    # ── Data ─────────────────────────────────────────────────────────────────
    with st.spinner(f"Running volume analysis on {ticker}…"):
        raw = fetch_ohlcv(ticker, period=period, interval=interval)

    if raw.empty:
        st.error("No data returned. Try a different period or interval.")
        return
    if len(raw) < 55:
        st.warning(f"Only {len(raw)} bars loaded — need 55+ for Wyckoff detection. Try a wider period.")

    result  = run_volume_analysis(raw)
    df      = result["enriched_df"]
    summary = result["summary"]
    vp      = result["vp"]

    # Attach VP levels to df for chart access
    df.attrs["poc"]   = vp["poc"]
    df.attrs["va_hi"] = vp["value_area_high"]
    df.attrs["va_lo"] = vp["value_area_low"]

    # ── Verdict + metrics ─────────────────────────────────────────────────────
    _verdict_card(summary)
    _method_metrics(summary)

    st.info(
        "**Important**: These signals infer large-player activity from *price + volume patterns* only. "
        "Without broker-level data, this cannot definitively identify a specific institution or 'bandar'. "
        "High VPIN + Absorption + Accumulation phase together is the strongest confluence signal available "
        "from public OHLCV data.",
        icon="ℹ️",
    )
    st.divider()

    # ── Main overview chart ───────────────────────────────────────────────────
    st.markdown("### 📊 Smart Money Overview")
    st.caption(
        "Phase background: 🟢 Accumulation · 📈 Markup · 🔴 Distribution · 📉 Markdown · "
        "💧 Spring · ⚠️ UTAD  |  ▲ = Bullish OBV divergence  |  ■ = Volume absorption bar"
    )
    fig_overview = smart_money_overview_chart(df, ticker)
    st.plotly_chart(fig_overview, use_container_width=True)

    st.divider()

    # ── Volume Profile + EVR side by side ─────────────────────────────────────
    col_vp, col_evr = st.columns([1, 1])
    with col_vp:
        st.markdown("### 📦 Volume Profile")
        st.caption("Yellow = Point of Control · Purple band = 70% Value Area")
        fig_vp = volume_profile_chart(vp, float(df["Close"].iloc[-1]))
        st.plotly_chart(fig_vp, use_container_width=True)
        _volume_profile_sidebar(summary)

    with col_evr:
        st.markdown("### ⚖️ Effort vs Result")
        st.caption(
            "High volume (effort) + tiny price move (result) = absorption by large player. "
            "Top-right = genuine breakout."
        )
        fig_evr = effort_vs_result_chart(result["evr"])
        st.plotly_chart(fig_evr, use_container_width=True)

    st.divider()

    # ── CMF + OBV ─────────────────────────────────────────────────────────────
    st.markdown("### 💰 Chaikin Money Flow + OBV")
    st.caption(
        "CMF > +0.05 = net buying pressure · CMF < -0.05 = net selling pressure. "
        "OBV rising while price falls = hidden accumulation (bullish divergence)."
    )
    fig_cmf = cmf_obv_chart(df)
    st.plotly_chart(fig_cmf, use_container_width=True)

    st.divider()

    # ── Wyckoff phase distribution ────────────────────────────────────────────
    st.markdown("### 🔄 Wyckoff Phase Distribution")
    fig_phase = wyckoff_phase_timeline(df)
    st.plotly_chart(fig_phase, use_container_width=True)

    # ── Method explainer ──────────────────────────────────────────────────────
    with st.expander("📖 How each method works"):
        st.markdown("""
**VPIN (Probability of Informed Trading)**
Splits volume into fixed-size buckets and measures buy/sell imbalance.
High VPIN (>0.7) means order flow is strongly one-sided — someone with
information is trading, not random retail noise. Watch for VPIN spikes.

**Effort vs Result (Wyckoff)**
If a bar has abnormally HIGH volume (effort) but a SMALL price range
(result), a large counterparty absorbed all that flow. On a down bar
this is a buy signal — the "bandar" is buying every share being sold.
On an up bar it's a distribution signal.

**Wyckoff Phase Detection**
Classifies market behaviour into 4 main phases + 2 trap events:
- *Accumulation*: sideways at lows, volume declining — smart money building
- *Markup*: rising price + volume — trend underway
- *Distribution*: sideways at highs, volume declining — smart money exiting
- *Markdown*: falling price + volume — trend down
- *Spring*: brief dip below support on LOW volume — a trap to shake out weak hands
- *UTAD*: brief spike above resistance on HIGH volume — a trap before distribution

**Volume Profile**
Shows which price levels have the most traded volume. The Point of
Control (POC) is where the most trading happened — institutions defend
this level. The Value Area (70% of volume) acts as a bracket.
Price outside the value area tends to return to it.

**Chaikin Money Flow + OBV Divergence**
CMF measures whether volume is flowing in or out net. OBV divergence
is the strongest signal: if the price makes a new LOW but OBV is
*rising*, someone is buying into every sell — classic accumulation.
        """)

    st.caption(
        "⚠️ All signals derived from OHLCV data only. "
        "Without Level-2 order book or broker data, institutional vs retail "
        "distinction is probabilistic, not definitive."
    )
