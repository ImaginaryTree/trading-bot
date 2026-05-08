"""
Scalping tab: renders the scalper dashboard in Streamlit.

Layout
    ① Sidebar parameters (interval, TP%, SL%)
    ② Live signal card (BUY/SELL/HOLD + TP/SL levels)
    ③ Indicator vote breakdown table
    ④ 4-panel scalp chart with signal markers
    ⑤ Historical signal log + net TP bar chart
    ⑥ Cost & risk summary
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import (
    IDX_WATCHLIST,
    LOT_SIZE,
    SCALP_INTERVALS,
    SCALP_PERIODS,
    SCALP_STOP_PCT,
    SCALP_TARGET_PCT,
)
from core.data import fetch_ohlcv
from core.scalp_indicators import add_all_scalp_indicators
from core.scalp_signals import scan_scalp_signals, scalp_signal
from ui.scalp_charts import scalp_price_chart, trade_log_chart
from utils.formatting import signal_emoji

_ACTION_BG = {
    "BUY":  ("rgba(38,166,154,0.12)", "#26a69a"),
    "SELL": ("rgba(239,83,80,0.12)",  "#ef5350"),
    "HOLD": ("rgba(255,193,7,0.12)",  "#ffc107"),
}


def _signal_card(sig: dict) -> None:
    """Render the prominent live signal card."""
    action  = sig["action"]
    bg, col = _ACTION_BG.get(action, ("rgba(128,128,128,0.1)", "gray"))
    emoji   = signal_emoji(action)
    score   = sig["score"]
    total   = sig["max_possible"]

    st.markdown(
        f"""
        <div style="
            background:{bg}; border:1.5px solid {col};
            border-radius:14px; padding:24px 28px; margin-bottom:12px;
        ">
          <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
            <div style="font-size:3rem; line-height:1">{emoji}</div>
            <div>
              <div style="font-size:2rem; font-weight:700; color:{col}">{action}</div>
              <div style="color:#aaa; font-size:0.85rem">
                Signal strength: {score}/{total} indicators agree
              </div>
            </div>
            <div style="margin-left:auto; text-align:right">
              <div style="font-size:1.4rem; font-weight:600; color:{col}">
                Rp {sig['entry_price']:,.0f}
              </div>
              <div style="color:#aaa; font-size:0.8rem">Entry price</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tp_sl_metrics(sig: dict, capital: int) -> None:
    """Render TP / SL / R:R / net profit metrics row."""
    action = sig["action"]
    c1, c2, c3, c4, c5 = st.columns(5)

    tp_label = "🎯 Take-profit" if action == "BUY" else "🎯 Cover at"
    sl_label = "🛑 Stop-loss"

    c1.metric(tp_label,   f"Rp {sig['take_profit']:,.0f}",
              f"+{sig['tp_pct']:.3f}%")
    c2.metric(sl_label,   f"Rp {sig['stop_loss']:,.0f}",
              f"-{sig['sl_pct']:.3f}%", delta_color="inverse")
    c3.metric("Risk : Reward", f"1 : {sig['risk_reward']:.2f}")
    c4.metric("Net profit to TP",
              f"{sig['net_tp_pct']:+.3f}%",
              f"after {sig['total_cost_pct']:.2f}% cost",
              delta_color="normal" if sig["net_tp_pct"] > 0 else "inverse")

    # Lot-based P&L estimate
    lots      = max(1, capital // (sig["entry_price"] * LOT_SIZE))
    shares    = lots * LOT_SIZE
    gross_pnl = (sig["take_profit"] - sig["entry_price"]) * shares
    c5.metric("Est. gross P&L",
              f"Rp {gross_pnl:+,.0f}",
              f"{lots} lot{'s' if lots != 1 else ''} ({shares:,} shares)")


def _vote_table(sig: dict) -> None:
    """Render the per-indicator vote breakdown."""
    rows = []
    for indicator, vote in sig["indicator_votes"].items():
        reason = sig["vote_reasons"].get(indicator, "")
        emoji  = signal_emoji(vote)
        rows.append({"Indicator": indicator, "Signal": f"{emoji} {vote}", "Reason": reason})

    df = pd.DataFrame(rows)

    def _color_signal(col):
        if col.name != "Signal":
            return [""] * len(col)
        styles = []
        for v in col:
            if "BUY"  in v: styles.append("color:#26a69a; font-weight:600")
            elif "SELL" in v: styles.append("color:#ef5350; font-weight:600")
            else:             styles.append("color:#ffc107; font-weight:600")
        return styles

    st.dataframe(
        df.style.apply(_color_signal),
        use_container_width=True,
        hide_index=True,
    )


def _trade_log_table(trade_log: pd.DataFrame) -> None:
    """Render paginated historical signal log."""
    if trade_log.empty:
        st.info("No trade signals found in this window. Try a wider period or lower min-score.")
        return

    display = trade_log.copy().reset_index()
    display["datetime"] = display["datetime"].dt.strftime("%Y-%m-%d %H:%M")
    display["price"]        = display["price"].map(lambda x: f"Rp {x:,.0f}")
    display["take_profit"]  = display["take_profit"].map(lambda x: f"Rp {x:,.0f}")
    display["stop_loss"]    = display["stop_loss"].map(lambda x: f"Rp {x:,.0f}")
    display["tp_pct"]       = display["tp_pct"].map(lambda x: f"{x:+.3f}%")
    display["net_tp_pct"]   = display["net_tp_pct"].map(lambda x: f"{x:+.3f}%")
    display["risk_reward"]  = display["risk_reward"].map(lambda x: f"1:{x:.2f}")
    display["action"]       = display["action"].map(lambda a: f"{signal_emoji(a)} {a}")

    display = display.rename(columns={
        "datetime": "Time", "action": "Action", "price": "Entry",
        "take_profit": "TP", "stop_loss": "SL",
        "tp_pct": "TP %", "net_tp_pct": "Net %",
        "risk_reward": "R:R", "score": "Score",
        "reason_summary": "Reason",
    })

    def _color_action(col):
        if col.name != "Action":
            return [""] * len(col)
        return [
            "color:#26a69a; font-weight:600" if "BUY"  in v else
            "color:#ef5350; font-weight:600" if "SELL" in v else
            "color:#ffc107; font-weight:600"
            for v in col
        ]

    st.dataframe(
        display[["Time","Action","Entry","TP","SL","TP %","Net %","R:R","Score","Reason"]]
        .style.apply(_color_action),
        use_container_width=True,
        hide_index=True,
    )

    buy_count  = (trade_log["action"] == "BUY").sum()
    sell_count = (trade_log["action"] == "SELL").sum()
    st.caption(f"Total signals: {len(trade_log)}  |  🟢 BUY: {buy_count}  |  🔴 SELL: {sell_count}")


# ── Public renderer ───────────────────────────────────────────────────────────

def render_scalping(ticker: str) -> None:
    st.subheader(f"⚡ Scalping — {ticker}  ·  {IDX_WATCHLIST.get(ticker, '')}")

    # ── Parameter bar ───────────────────────────────────────────────────────
    with st.expander("⚙️ Scalping parameters", expanded=False):
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        interval   = pc1.selectbox("Interval",    SCALP_INTERVALS, index=1, key="scalp_int")
        period     = pc2.selectbox("Period",       SCALP_PERIODS,   index=0, key="scalp_per")
        tp_pct     = pc3.slider("Take-profit %",   0.1, 2.0, SCALP_TARGET_PCT * 100, 0.05, key="scalp_tp") / 100
        sl_pct     = pc4.slider("Stop-loss %",     0.1, 2.0, SCALP_STOP_PCT   * 100, 0.05, key="scalp_sl") / 100
        capital    = pc5.number_input("Capital (Rp)", min_value=1_000_000,
                                      value=10_000_000, step=1_000_000, key="scalp_cap")

    # ── Fetch + enrich ───────────────────────────────────────────────────────
    with st.spinner(f"Loading {ticker} scalp data ({interval})…"):
        df = fetch_ohlcv(ticker, period=period, interval=interval)

    if df.empty:
        st.error("No data returned. For 1m/2m data, period must be '1d' or '5d'.")
        return

    df = add_all_scalp_indicators(df)

    # ── Current signal ───────────────────────────────────────────────────────
    sig = scalp_signal(df, tp_pct=tp_pct, sl_pct=sl_pct)

    _signal_card(sig)

    if sig["action"] == "HOLD":
        st.warning(
            f"Only {sig['score']}/{sig['max_possible']} indicators agree — "
            "below minimum threshold. Waiting for clearer setup."
        )
    else:
        _tp_sl_metrics(sig, capital)

    st.divider()

    # ── Chart ────────────────────────────────────────────────────────────────
    with st.spinner("Scanning historical signals…"):
        trade_log = scan_scalp_signals(df, tp_pct=tp_pct, sl_pct=sl_pct)

    fig = scalp_price_chart(df, trade_log, ticker, sig)
    st.plotly_chart(fig, use_container_width=True)

    # ── Indicator detail ─────────────────────────────────────────────────────
    col_vote, col_atr = st.columns([2, 1])
    with col_vote:
        st.markdown("**Indicator votes**")
        _vote_table(sig)
    with col_atr:
        st.markdown("**Volatility**")
        atr = sig.get("atr")
        st.metric("ATR (7)", f"Rp {atr:,.1f}" if atr else "—")
        st.metric("ATR / Price", f"{atr / sig['entry_price'] * 100:.3f}%" if atr and sig["entry_price"] else "—")
        st.metric("Spread cost", f"{sig['total_cost_pct']:.3f}%")
        rr = sig["risk_reward"]
        st.metric("Risk : Reward", f"1 : {rr:.2f}",
                  "✅ Good" if rr >= 1.5 else "⚠️ Tight")

    st.divider()

    # ── Historical trade log ─────────────────────────────────────────────────
    st.markdown("**Historical signals in window**")
    _trade_log_table(trade_log)

    log_fig = trade_log_chart(trade_log)
    if log_fig:
        st.plotly_chart(log_fig, use_container_width=True)

    st.caption(
        "⚠️ Scalping signals are for educational purposes only. "
        "IDX tick sizes, liquidity, and 0.1% sell tax significantly affect small-target trades."
    )
