"""
Scalping charts: Plotly figures for the scalper tab.
Returns go.Figure — no Streamlit imports.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_TEMPLATE = "plotly_dark"
_BUY_COLOR  = "#26a69a"
_SELL_COLOR = "#ef5350"
_HOLD_COLOR = "#ffc107"


def scalp_price_chart(
    df: pd.DataFrame,
    trade_log: pd.DataFrame,
    ticker: str,
    current_signal: dict,
) -> go.Figure:
    """4-panel scalp chart: price+EMA+VWAP / RSI-7 / Stochastic / Momentum."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.50, 0.18, 0.18, 0.14],
        vertical_spacing=0.03,
        subplot_titles=(
            f"{ticker} — Scalp view",
            "RSI (7)",
            "Stochastic",
            "3-bar Momentum %",
        ),
    )

    # ── Panel 1: candlestick + EMAs + VWAP ─────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=_BUY_COLOR, decreasing_line_color=_SELL_COLOR,
    ), row=1, col=1)

    ema_fast_col = [c for c in df.columns if c.startswith("EMA_") and "5" in c]
    ema_slow_col = [c for c in df.columns if c.startswith("EMA_") and "13" in c]

    if ema_fast_col:
        fig.add_trace(go.Scatter(x=df.index, y=df[ema_fast_col[0]],
            name="EMA 5", line=dict(color="#FFD54F", width=1.5)), row=1, col=1)
    if ema_slow_col:
        fig.add_trace(go.Scatter(x=df.index, y=df[ema_slow_col[0]],
            name="EMA 13", line=dict(color="#FF8A65", width=1.5)), row=1, col=1)
    if "VWAP" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"],
            name="VWAP", line=dict(color="#CE93D8", width=1.5, dash="dot")), row=1, col=1)

    # TP / SL reference lines on price panel
    if current_signal["action"] != "HOLD":
        tp_color = _BUY_COLOR if current_signal["action"] == "BUY" else _SELL_COLOR
        sl_color = _SELL_COLOR if current_signal["action"] == "BUY" else _BUY_COLOR
        fig.add_hline(y=current_signal["take_profit"],
            line=dict(color=tp_color, dash="dash", width=1),
            annotation_text=f"TP Rp {current_signal['take_profit']:,.0f}",
            annotation_position="right", row=1, col=1)
        fig.add_hline(y=current_signal["stop_loss"],
            line=dict(color=sl_color, dash="dash", width=1),
            annotation_text=f"SL Rp {current_signal['stop_loss']:,.0f}",
            annotation_position="right", row=1, col=1)

    # Trade log markers
    if not trade_log.empty:
        buy_log  = trade_log[trade_log["action"] == "BUY"]
        sell_log = trade_log[trade_log["action"] == "SELL"]

        if not buy_log.empty:
            fig.add_trace(go.Scatter(
                x=buy_log.index, y=buy_log["price"],
                mode="markers", name="BUY signal",
                marker=dict(symbol="triangle-up", size=12, color=_BUY_COLOR,
                            line=dict(width=1, color="white")),
            ), row=1, col=1)
        if not sell_log.empty:
            fig.add_trace(go.Scatter(
                x=sell_log.index, y=sell_log["price"],
                mode="markers", name="SELL signal",
                marker=dict(symbol="triangle-down", size=12, color=_SELL_COLOR,
                            line=dict(width=1, color="white")),
            ), row=1, col=1)

    # ── Panel 2: RSI-7 ──────────────────────────────────────────────────────
    rsi_col = [c for c in df.columns if c.startswith("RSI_")]
    if rsi_col:
        fig.add_trace(go.Scatter(x=df.index, y=df[rsi_col[0]],
            name="RSI 7", line=dict(color="#CE93D8", width=1.5), showlegend=False), row=2, col=1)
        fig.add_hline(y=65, line=dict(color=_SELL_COLOR, dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=35, line=dict(color=_BUY_COLOR,  dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=50, line=dict(color="gray",       dash="dot",  width=0.5), row=2, col=1)

    # ── Panel 3: Stochastic ─────────────────────────────────────────────────
    if "Stoch_K" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_K"],
            name="%K", line=dict(color="#80DEEA", width=1.5), showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_D"],
            name="%D", line=dict(color="#FFCC80", width=1.2, dash="dot"), showlegend=False), row=3, col=1)
        fig.add_hline(y=80, line=dict(color=_SELL_COLOR, dash="dash", width=0.8), row=3, col=1)
        fig.add_hline(y=20, line=dict(color=_BUY_COLOR,  dash="dash", width=0.8), row=3, col=1)

    # ── Panel 4: Momentum ───────────────────────────────────────────────────
    mom_col = [c for c in df.columns if c.startswith("Momentum_")]
    if mom_col:
        mom = df[mom_col[0]].fillna(0)
        colors = [_BUY_COLOR if v >= 0 else _SELL_COLOR for v in mom]
        fig.add_trace(go.Bar(x=df.index, y=mom, name="Momentum",
            marker_color=colors, showlegend=False), row=4, col=1)
        fig.add_hline(y=0, line=dict(color="gray", dash="dot", width=0.5), row=4, col=1)

    fig.update_layout(
        template=_TEMPLATE,
        height=720,
        margin=dict(l=10, r=80, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)")
    return fig


def trade_log_chart(trade_log: pd.DataFrame) -> go.Figure | None:
    """Bar chart of net TP% per signal in the historical log."""
    if trade_log.empty:
        return None

    fig = go.Figure()
    colors = [_BUY_COLOR if a == "BUY" else _SELL_COLOR for a in trade_log["action"]]
    fig.add_trace(go.Bar(
        x=trade_log.index,
        y=trade_log["net_tp_pct"],
        marker_color=colors,
        text=[f"{v:+.3f}%" for v in trade_log["net_tp_pct"]],
        textposition="outside",
        name="Net TP %",
    ))
    fig.add_hline(y=0, line=dict(color="gray", dash="dot", width=0.8))
    fig.update_layout(
        template=_TEMPLATE,
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Net profit to TP (%)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
