"""
Volume analysis charts: six Plotly figures for the smart money tab.
All return go.Figure — no Streamlit imports.
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

_PHASE_COLORS = {
    "ACCUMULATION": "#26a69a",
    "MARKUP":       "#80DEEA",
    "DISTRIBUTION": "#ef5350",
    "MARKDOWN":     "#FF8A65",
    "SPRING":       "#B9F6CA",
    "UTAD":         "#FF5252",
    "UNCLEAR":      "rgba(128,128,128,0.3)",
}


# ── 1. Main price + Wyckoff phase + Smart score ───────────────────────────────

def smart_money_overview_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    3-panel: Candlestick + POC/VA lines + Wyckoff phase bands
             Smart Money Score bar
             VPIN line
    """
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} — Smart Money View", "Smart Money Score", "VPIN"),
    )

    # ── Panel 1: candles + phase background ──────────────────────────────────
    if "wyckoff_phase" in df.columns:
        for i in range(len(df) - 1):
            phase = df["wyckoff_phase"].iloc[i]
            color = _PHASE_COLORS.get(phase, "rgba(0,0,0,0)")
            if phase != "UNCLEAR":
                fig.add_vrect(
                    x0=df.index[i], x1=df.index[i + 1],
                    fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba")
                    if color.startswith("rgb") else color,
                    line_width=0, row=1, col=1,
                )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color=_BUY, decreasing_line_color=_SELL,
    ), row=1, col=1)

    # POC and Value Area lines
    if "poc" in df.attrs:
        poc = df.attrs["poc"]
        va_hi = df.attrs.get("va_hi")
        va_lo = df.attrs.get("va_lo")
        fig.add_hline(y=poc, line=dict(color=_GOLD, dash="dash", width=1.5),
                      annotation_text=f"POC {poc:,.0f}", row=1, col=1)
        if va_hi:
            fig.add_hline(y=va_hi, line=dict(color=_PURP, dash="dot", width=1),
                          annotation_text="VAH", row=1, col=1)
        if va_lo:
            fig.add_hline(y=va_lo, line=dict(color=_PURP, dash="dot", width=1),
                          annotation_text="VAL", row=1, col=1)

    # OBV divergence markers
    if "obv_div" in df.columns:
        bull_div = df[df["obv_div"] == "BULLISH_DIV"]
        bear_div = df[df["obv_div"] == "BEARISH_DIV"]
        if not bull_div.empty:
            fig.add_trace(go.Scatter(
                x=bull_div.index, y=bull_div["Low"] * 0.995,
                mode="markers", name="Bullish OBV div",
                marker=dict(symbol="triangle-up", size=10, color=_BUY,
                            line=dict(width=1, color="white")),
            ), row=1, col=1)
        if not bear_div.empty:
            fig.add_trace(go.Scatter(
                x=bear_div.index, y=bear_div["High"] * 1.005,
                mode="markers", name="Bearish OBV div",
                marker=dict(symbol="triangle-down", size=10, color=_SELL,
                            line=dict(width=1, color="white")),
            ), row=1, col=1)

    # EVR absorption markers
    if "evr_signal" in df.columns:
        abs_buy  = df[df["evr_signal"] == "ABSORPTION_BUY"]
        abs_sell = df[df["evr_signal"] == "ABSORPTION_SELL"]
        if not abs_buy.empty:
            fig.add_trace(go.Scatter(
                x=abs_buy.index, y=abs_buy["Low"] * 0.998,
                mode="markers", name="Absorption (buy)",
                marker=dict(symbol="square", size=8, color="#B9F6CA",
                            line=dict(width=1, color="white")),
            ), row=1, col=1)
        if not abs_sell.empty:
            fig.add_trace(go.Scatter(
                x=abs_sell.index, y=abs_sell["High"] * 1.002,
                mode="markers", name="Absorption (sell)",
                marker=dict(symbol="square", size=8, color="#FF5252",
                            line=dict(width=1, color="white")),
            ), row=1, col=1)

    # ── Panel 2: Smart Money Score ────────────────────────────────────────────
    if "smart_score" in df.columns:
        score = df["smart_score"].fillna(0)
        colors = [_BUY if v >= 0 else _SELL for v in score]
        fig.add_trace(go.Bar(
            x=df.index, y=score, name="Smart score",
            marker_color=colors, showlegend=False,
        ), row=2, col=1)
        fig.add_hline(y=0.6,  line=dict(color=_BUY,  dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=-0.6, line=dict(color=_SELL, dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=0,    line=dict(color="gray", dash="dot", width=0.5), row=2, col=1)

    # ── Panel 3: VPIN ─────────────────────────────────────────────────────────
    if "VPIN" in df.columns:
        vpin = df["VPIN"].fillna(0)
        vpin_colors = [_SELL if v > 0.7 else _GOLD if v > 0.5 else _NEUT for v in vpin]
        fig.add_trace(go.Scatter(
            x=df.index, y=vpin, name="VPIN",
            fill="tozeroy", fillcolor="rgba(144,164,174,0.15)",
            line=dict(color=_NEUT, width=1.5), showlegend=False,
        ), row=3, col=1)
        fig.add_hline(y=0.70, line=dict(color=_SELL, dash="dash", width=0.8),
                      annotation_text="Informed", row=3, col=1)
        fig.add_hline(y=0.50, line=dict(color=_GOLD, dash="dot", width=0.6), row=3, col=1)

    fig.update_layout(
        template=_T, height=760,
        margin=dict(l=10, r=100, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
    return fig


# ── 2. Volume Profile horizontal bar chart ────────────────────────────────────

def volume_profile_chart(vp: dict, current_price: float) -> go.Figure:
    """Horizontal bar chart showing volume at each price level."""
    centers = vp["centers"]
    vols    = vp["vol_by_price"]
    poc     = vp["poc"]
    vah     = vp["value_area_high"]
    val     = vp["value_area_low"]

    colors = []
    for c, v in zip(centers, vols):
        if abs(c - poc) < (centers[1] - centers[0]) * 0.6:
            colors.append(_GOLD)
        elif val <= c <= vah:
            colors.append("rgba(92,107,192,0.7)")
        else:
            colors.append("rgba(128,128,128,0.4)")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=centers, x=vols,
        orientation="h",
        marker_color=colors,
        name="Volume",
        showlegend=False,
    ))

    # Current price line
    fig.add_hline(y=current_price,
                  line=dict(color="white", dash="dash", width=1.5),
                  annotation_text=f"Price {current_price:,.0f}")
    fig.add_hline(y=poc,
                  line=dict(color=_GOLD, dash="dot", width=1),
                  annotation_text=f"POC {poc:,.0f}")
    fig.add_hline(y=vah,
                  line=dict(color=_PURP, dash="dot", width=0.8),
                  annotation_text="VAH")
    fig.add_hline(y=val,
                  line=dict(color=_PURP, dash="dot", width=0.8),
                  annotation_text="VAL")

    fig.update_layout(
        template=_T, height=420,
        title="Volume Profile",
        xaxis_title="Volume",
        yaxis_title="Price (IDR)",
        margin=dict(l=10, r=80, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── 3. Effort vs Result scatter ───────────────────────────────────────────────

def effort_vs_result_chart(evr: pd.DataFrame) -> go.Figure:
    """Scatter: Effort (vol z-score) vs Result (range z-score). Quadrants matter."""
    colors = {
        "ABSORPTION_BUY":  _BUY,
        "ABSORPTION_SELL": _SELL,
        "BREAKOUT":        _GOLD,
        "NORMAL":          "rgba(128,128,128,0.3)",
    }
    sizes = {
        "ABSORPTION_BUY": 12, "ABSORPTION_SELL": 12,
        "BREAKOUT": 14, "NORMAL": 6,
    }

    fig = go.Figure()
    for sig, color in colors.items():
        mask = evr["evr_signal"] == sig
        if mask.sum() == 0:
            continue
        fig.add_trace(go.Scatter(
            x=evr.loc[mask, "effort"],
            y=evr.loc[mask, "result"],
            mode="markers",
            name=sig.replace("_", " ").title(),
            marker=dict(color=color, size=sizes[sig],
                        line=dict(width=0.5, color="white")),
        ))

    fig.add_vline(x=0, line=dict(color="gray", dash="dot", width=0.8))
    fig.add_hline(y=0, line=dict(color="gray", dash="dot", width=0.8))

    # Quadrant labels
    for x, y, txt in [(2, -1.5, "🔴 Absorption\n(sell)"),
                       (2,  1.5, "🚀 Breakout"),
                       (-1.5, -1.5, "Normal"),
                       (-1.5,  1.5, "Normal"),
                       (1, -2.5, "🟢 Absorption\n(buy)")]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(size=10, color="rgba(200,200,200,0.5)"))

    fig.update_layout(
        template=_T, height=380,
        title="Effort vs Result (volume z-score vs range z-score)",
        xaxis_title="Effort (volume z-score)",
        yaxis_title="Result (range z-score)",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── 4. CMF + OBV chart ────────────────────────────────────────────────────────

def cmf_obv_chart(df: pd.DataFrame) -> go.Figure:
    """2-panel: OBV with divergence markers / CMF."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.5, 0.5], vertical_spacing=0.05,
                        subplot_titles=("On-Balance Volume (OBV)", "Chaikin Money Flow (CMF)"))

    # OBV
    if "OBV" in df.columns:
        obv = df["OBV"]
        fig.add_trace(go.Scatter(
            x=df.index, y=obv, name="OBV",
            fill="tozeroy",
            fillcolor="rgba(92,107,192,0.15)",
            line=dict(color="#5C6BC0", width=1.5),
            showlegend=False,
        ), row=1, col=1)

    # CMF bars
    if "CMF" in df.columns:
        cmf    = df["CMF"].fillna(0)
        colors = [_BUY if v >= 0 else _SELL for v in cmf]
        fig.add_trace(go.Bar(
            x=df.index, y=cmf, name="CMF",
            marker_color=colors, showlegend=False,
        ), row=2, col=1)
        fig.add_hline(y=0.05,  line=dict(color=_BUY,  dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=-0.05, line=dict(color=_SELL, dash="dash", width=0.8), row=2, col=1)
        fig.add_hline(y=0,     line=dict(color="gray", dash="dot", width=0.5), row=2, col=1)

    fig.update_layout(
        template=_T, height=420,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
    return fig


# ── 5. Wyckoff phase timeline ─────────────────────────────────────────────────

def wyckoff_phase_timeline(df: pd.DataFrame) -> go.Figure:
    """Stacked area showing how much time is spent in each Wyckoff phase."""
    if "wyckoff_phase" not in df.columns:
        return go.Figure()

    counts = df["wyckoff_phase"].value_counts()
    total  = counts.sum()

    fig = go.Figure(go.Bar(
        x=counts.index,
        y=(counts / total * 100).round(1),
        marker_color=[_PHASE_COLORS.get(p, _NEUT) for p in counts.index],
        text=[f"{v:.1f}%" for v in (counts / total * 100)],
        textposition="outside",
    ))
    fig.update_layout(
        template=_T, height=280,
        title="Wyckoff phase distribution (% of bars)",
        yaxis_title="% of time",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig
