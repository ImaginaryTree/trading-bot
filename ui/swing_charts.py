"""
Swing trade charts — Plotly figures for the swing tab.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_T    = "plotly_dark"
_BUY  = "#26a69a"
_SELL = "#ef5350"
_NEUT = "#90A4AE"
_GOLD = "#FFD54F"
_PURP = "#CE93D8"
_BLUE = "#80DEEA"


# ── 1. Ichimoku cloud chart ───────────────────────────────────────────────────

def ichimoku_chart(df: pd.DataFrame, result: dict, ticker: str) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.72, 0.28], vertical_spacing=0.03,
                        subplot_titles=(f"{ticker} — Ichimoku Cloud", "MACD"))

    # Cloud fill
    if "ichi_span_a" in df.columns and "ichi_span_b" in df.columns:
        span_a = df["ichi_span_a"]
        span_b = df["ichi_span_b"]
        # Green cloud (bullish)
        fig.add_trace(go.Scatter(x=df.index, y=span_a, line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=span_b,
                                 fill="tonexty",
                                 fillcolor=[
                                     "rgba(38,166,154,0.15)" if a >= b else "rgba(239,83,80,0.15)"
                                     for a, b in zip(span_a.fillna(0), span_b.fillna(0))
                                 ][0] if len(span_a) > 0 else "rgba(128,128,128,0.1)",
                                 line=dict(width=0), name="Cloud",
                                 hoverinfo="skip", showlegend=False), row=1, col=1)

        # Simpler approach: two separate fills
        green_mask = span_a >= span_b
        for label, color, top, bot in [
            ("Bullish cloud", "rgba(38,166,154,0.18)", span_a, span_b),
            ("Bearish cloud", "rgba(239,83,80,0.18)",  span_b, span_a),
        ]:
            fig.add_trace(go.Scatter(
                x=list(df.index) + list(df.index[::-1]),
                y=list(top.fillna(0)) + list(bot.fillna(0))[::-1],
                fill="toself", fillcolor=color, line=dict(width=0),
                name=label, hoverinfo="skip", showlegend=True,
            ), row=1, col=1)

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=_BUY, decreasing_line_color=_SELL,
    ), row=1, col=1)

    # Ichimoku lines
    line_map = [
        ("ichi_tenkan", _GOLD, "Tenkan (9)"),
        ("ichi_kijun",  _PURP, "Kijun (26)"),
        ("ichi_span_a", _BUY,  "Span A"),
        ("ichi_span_b", _SELL, "Span B"),
    ]
    for col, color, name in line_map:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=name,
                line=dict(color=color, width=1.2),
            ), row=1, col=1)

    # TP / SL levels
    _add_tpsl(fig, result, row=1)

    # MACD panel
    if "macd" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"],
            name="MACD", line=dict(color=_BLUE, width=1.5), showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd_sig"],
            name="Signal", line=dict(color=_GOLD, width=1.2), showlegend=False), row=2, col=1)
        hist = df["macd_hist"].fillna(0)
        fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
            marker_color=[_BUY if v >= 0 else _SELL for v in hist],
            showlegend=False), row=2, col=1)

    _layout(fig, height=680)
    return fig


# ── 2. Supertrend + Elder chart ───────────────────────────────────────────────

def supertrend_elder_chart(df: pd.DataFrame, result: dict, ticker: str) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.55, 0.22, 0.23], vertical_spacing=0.03,
                        subplot_titles=(f"{ticker} — Supertrend", "Elder EMA", "Elder Stochastic"))

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=_BUY, decreasing_line_color=_SELL,
    ), row=1, col=1)

    # Supertrend line (color changes with direction)
    if "supertrend" in df.columns and "st_direction" in df.columns:
        st   = df["supertrend"]
        dirn = df["st_direction"]
        # Split into bullish/bearish segments
        bull_st = st.where(dirn == 1)
        bear_st = st.where(dirn == -1)
        fig.add_trace(go.Scatter(x=df.index, y=bull_st, name="Supertrend (bull)",
            line=dict(color=_BUY, width=2), connectgaps=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bear_st, name="Supertrend (bear)",
            line=dict(color=_SELL, width=2), connectgaps=False), row=1, col=1)

    _add_tpsl(fig, result, row=1)

    # Elder EMA
    if "elder_ema" in df.columns:
        slope = df["elder_ema_slope"].fillna(0)
        fig.add_trace(go.Scatter(x=df.index, y=df["elder_ema"], name="Elder EMA",
            line=dict(color=_GOLD, width=2)), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=slope, name="EMA slope",
            marker_color=[_BUY if v >= 0 else _SELL for v in slope],
            showlegend=False), row=2, col=1)

    # Stochastic
    if "elder_stoch_k" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["elder_stoch_k"], name="%K",
            line=dict(color=_BLUE, width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["elder_stoch_d"], name="%D",
            line=dict(color=_PURP, width=1.2, dash="dot")), row=3, col=1)
        for level, color in [(80, _SELL), (20, _BUY)]:
            fig.add_hline(y=level, line=dict(color=color, dash="dash", width=0.8), row=3, col=1)

    _layout(fig, height=680)
    return fig


# ── 3. Fibonacci + S/R chart ──────────────────────────────────────────────────

def fibonacci_sr_chart(df: pd.DataFrame, result: dict, ticker: str) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=_BUY, decreasing_line_color=_SELL,
    ))

    # Fibonacci levels
    fib  = result["fib"]
    trend = fib["trend"]
    fib_colors = {
        "fib_0":    "rgba(255,255,255,0.3)",
        "fib_236":  "rgba(255,213,79,0.5)",
        "fib_382":  "rgba(38,166,154,0.8)",
        "fib_500":  "rgba(206,147,216,0.8)",
        "fib_618":  "rgba(38,166,154,0.8)",
        "fib_786":  "rgba(255,213,79,0.5)",
        "fib_1000": "rgba(255,255,255,0.3)",
    }
    for key, price_level in fib["levels"].items():
        short_key = key.replace("fib_", "")
        label = f"{int(short_key)/10:.1f}%" if len(short_key) == 3 else f"{short_key}%"
        color = fib_colors.get(key, "rgba(128,128,128,0.4)")
        fig.add_hline(y=price_level, line=dict(color=color, dash="dot", width=1),
                      annotation_text=f"Fib {label}  Rp {price_level:,.0f}",
                      annotation_position="right")

    # Support / Resistance
    sr = result["sr"]
    for r in (sr["resistance_levels"] or [])[:3]:
        fig.add_hline(y=r, line=dict(color=_SELL, dash="dash", width=1),
                      annotation_text=f"R {r:,.0f}", annotation_position="left")
    for s in (sr["support_levels"] or [])[:3]:
        fig.add_hline(y=s, line=dict(color=_BUY, dash="dash", width=1),
                      annotation_text=f"S {s:,.0f}", annotation_position="left")

    _add_tpsl(fig, result)

    fig.update_layout(
        template=_T, title=f"{ticker} — Fibonacci Retracement & S/R Levels",
        height=560, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=160, t=40, b=10),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
    return fig


# ── 4. Confluence radar chart ─────────────────────────────────────────────────

def confluence_radar(signals: dict) -> go.Figure:
    """Spider/radar chart showing each strategy's signal strength."""
    names    = list(signals.keys())
    strengths = []
    colors   = []
    for s in signals.values():
        val = s["strength"] if s["action"] == "BUY" else -s["strength"] if s["action"] == "SELL" else 0
        strengths.append(val)
        colors.append(_BUY if val > 0 else _SELL if val < 0 else _NEUT)

    # Map to 0–3 positive scale for radar (direction shown by color)
    abs_strengths = [abs(v) for v in strengths]

    fig = go.Figure(go.Scatterpolar(
        r=abs_strengths + [abs_strengths[0]],
        theta=names + [names[0]],
        fill="toself",
        fillcolor="rgba(92,107,192,0.15)",
        line=dict(color="#5C6BC0", width=2),
        name="Signal strength",
    ))

    fig.update_layout(
        template=_T, height=340,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 3], gridcolor="rgba(128,128,128,0.2)"),
            angularaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        title="Strategy confluence",
    )
    return fig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_tpsl(fig: go.Figure, result: dict, row: int = 1, col: int = 1) -> None:
    verdict = result["verdict"]
    if verdict == "WAIT":
        return
    tp_color = _BUY  if verdict == "BUY" else _SELL
    sl_color = _SELL if verdict == "BUY" else _BUY
    kwargs   = dict(row=row, col=col) if row > 1 else {}

    for price, label, color in [
        (result["target_3"], f"T3 {result['target_3']:,.0f}", tp_color),
        (result["target_2"], f"T2 {result['target_2']:,.0f}", tp_color),
        (result["target_1"], f"T1 {result['target_1']:,.0f}", tp_color),
        (result["stop_loss"], f"SL {result['stop_loss']:,.0f}", sl_color),
    ]:
        if row > 1:
            fig.add_hline(y=price, line=dict(color=color, dash="dash", width=1),
                          annotation_text=label, annotation_position="right", **kwargs)
        else:
            fig.add_hline(y=price, line=dict(color=color, dash="dash", width=1),
                          annotation_text=label, annotation_position="right")


def _layout(fig: go.Figure, height: int = 600) -> None:
    fig.update_layout(
        template=_T, height=height,
        margin=dict(l=10, r=120, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
