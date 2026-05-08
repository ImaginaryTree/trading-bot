"""
Quant charts: Plotly figures for the quant analytics tab.
All functions return go.Figure — zero Streamlit imports.
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
_MC   = "#5C6BC0"

# ── Buy / Sell volume charts ──────────────────────────────────────────────────

def buy_sell_volume_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    4-panel chart:
      Panel 1 — Candlestick + VWAP pressure overlay
      Panel 2 — Buy vs Sell volume bars side by side
      Panel 3 — Net delta (signed order flow)
      Panel 4 — Cumulative delta (order flow trend)
    """
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.40, 0.22, 0.20, 0.18],
        vertical_spacing=0.025,
        subplot_titles=(
            f"{ticker} — Price",
            "Buy vs Sell Volume",
            "Net Delta (Buy − Sell)",
            "Cumulative Delta",
        ),
    )

    # ── Panel 1: candles ──────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"], name="OHLC",
        increasing_line_color=_BUY, decreasing_line_color=_SELL,
    ), row=1, col=1)

    # Pressure background bands (subtle)
    if "pressure" in df.columns:
        for i in range(len(df) - 1):
            color = (
                "rgba(38,166,154,0.07)"  if df["pressure"].iloc[i] == "BUY"  else
                "rgba(239,83,80,0.07)"   if df["pressure"].iloc[i] == "SELL" else
                None
            )
            if color:
                fig.add_vrect(
                    x0=df.index[i], x1=df.index[i + 1],
                    fillcolor=color, line_width=0, row=1, col=1,
                )

    # VWAP pressure line
    if "vwap_pressure" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["vwap_pressure"],
            name="VWAP pressure", line=dict(color="#CE93D8", width=1.5),
            visible="legendonly",
        ), row=1, col=1)

    # ── Panel 2: buy/sell volume bars ─────────────────────────────────────────
    if "buy_vol" in df.columns:
        fig.add_trace(go.Bar(
            x=df.index, y=df["buy_vol"], name="Buy vol",
            marker_color=_BUY, opacity=0.85,
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=df.index, y=-df["sell_vol"], name="Sell vol",
            marker_color=_SELL, opacity=0.85,
        ), row=2, col=1)
        fig.add_hline(y=0, line=dict(color="gray", width=0.6), row=2, col=1)

        # Smoothed delta overlay on volume panel
        if "delta_smooth" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["delta_smooth"],
                name="Delta (smoothed)", line=dict(color="#FFD54F", width=1.5),
                showlegend=True,
            ), row=2, col=1)

    # ── Panel 3: net delta ────────────────────────────────────────────────────
    if "net_delta" in df.columns:
        delta_colors = [_BUY if v >= 0 else _SELL for v in df["net_delta"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["net_delta"], name="Net delta",
            marker_color=delta_colors, showlegend=False,
        ), row=3, col=1)
        fig.add_hline(y=0, line=dict(color="gray", width=0.6), row=3, col=1)

    # ── Panel 4: cumulative delta ─────────────────────────────────────────────
    if "cum_delta" in df.columns:
        cd = df["cum_delta"]
        cd_colors = [_BUY if v >= 0 else _SELL for v in cd.fillna(0)]
        fig.add_trace(go.Scatter(
            x=df.index, y=cd, name="Cum. delta",
            fill="tozeroy",
            line=dict(color=_BUY if float(cd.iloc[-1]) >= 0 else _SELL, width=2),
            fillcolor=(
                "rgba(38,166,154,0.15)" if float(cd.iloc[-1]) >= 0
                else "rgba(239,83,80,0.15)"
            ),
            showlegend=False,
        ), row=4, col=1)
        fig.add_hline(y=0, line=dict(color="gray", width=0.6), row=4, col=1)

    fig.update_layout(
        template=_T, height=780,
        margin=dict(l=10, r=10, t=40, b=10),
        barmode="overlay",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
    return fig


def flow_imbalance_gauge(imbalance: float) -> go.Figure:
    """Radial gauge showing buy/sell pressure balance."""
    buy_pct  = round(imbalance * 100, 1)
    sell_pct = round(100 - buy_pct, 1)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=buy_pct,
        number={"suffix": "% buy", "font": {"size": 22}},
        delta={"reference": 50, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": _BUY if buy_pct >= 50 else _SELL, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  35], "color": "rgba(239,83,80,0.25)"},
                {"range": [35, 65], "color": "rgba(128,128,128,0.12)"},
                {"range": [65,100], "color": "rgba(38,166,154,0.25)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": buy_pct,
            },
        },
        title={"text": "Flow imbalance", "font": {"size": 14}},
    ))
    fig.update_layout(
        template=_T, height=220,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Monte Carlo charts ────────────────────────────────────────────────────────

def monte_carlo_chart(mc: dict, ticker: str) -> go.Figure:
    """
    Monte Carlo fan chart:
      • Faint spaghetti lines for a sample of paths
      • Filled confidence bands (5–95, 25–75)
      • Median path highlighted
      • Dashed current-price reference line
    """
    if not mc:
        return go.Figure()

    paths  = mc["paths"]           # (n_sims, horizon)
    pcts   = mc["percentiles"]
    last   = mc["last_price"]
    n_sims = mc["n_sims"]
    horizon = mc["horizon"]

    # X axis: bar index ahead
    x_future = list(range(1, horizon + 1))
    x_hist   = [0]

    fig = go.Figure()

    # Sample of individual paths (faint)
    n_display = min(80, n_sims)
    sample_idx = np.linspace(0, n_sims - 1, n_display, dtype=int)
    for i in sample_idx:
        fig.add_trace(go.Scatter(
            x=x_future, y=paths[i],
            mode="lines",
            line=dict(color="rgba(92,107,192,0.08)", width=0.8),
            showlegend=False, hoverinfo="skip",
        ))

    # Confidence bands
    band_styles = [
        ("p95", "p5",  "rgba(92,107,192,0.12)", "90% range"),
        ("p75", "p25", "rgba(92,107,192,0.22)", "50% range"),
    ]
    for upper_k, lower_k, fill_color, name in band_styles:
        fig.add_trace(go.Scatter(
            x=x_future + x_future[::-1],
            y=list(pcts[upper_k]) + list(pcts[lower_k])[::-1],
            fill="toself", fillcolor=fill_color,
            line=dict(width=0), name=name,
            hoverinfo="skip",
        ))

    # Percentile lines
    pct_styles = {
        "p95": ("rgba(38,166,154,0.6)",  "95th pct"),
        "p75": ("rgba(38,166,154,0.9)",  "75th pct"),
        "p50": ("white",                 "Median"),
        "p25": ("rgba(239,83,80,0.9)",   "25th pct"),
        "p5":  ("rgba(239,83,80,0.6)",   "5th pct"),
    }
    for key, (color, label) in pct_styles.items():
        width = 2.5 if key == "p50" else 1.2
        fig.add_trace(go.Scatter(
            x=x_future, y=pcts[key],
            mode="lines", name=label,
            line=dict(color=color, width=width,
                      dash="dash" if key in ("p95", "p5") else "solid"),
        ))

    # Current price anchor point
    fig.add_trace(go.Scatter(
        x=[0], y=[last],
        mode="markers", name="Now",
        marker=dict(size=10, color="white", symbol="circle",
                    line=dict(color=_MC, width=2)),
    ))

    # Reference line at current price
    fig.add_hline(
        y=last,
        line=dict(color="rgba(255,255,255,0.3)", dash="dot", width=1),
        annotation_text=f"Current Rp {last:,.0f}",
        annotation_position="left",
    )

    fig.update_layout(
        template=_T,
        title=dict(
            text=f"{ticker} — Monte Carlo ({n_sims:,} paths, {horizon}-bar horizon)",
            font=dict(size=14),
        ),
        height=460,
        xaxis_title="Bars ahead",
        yaxis_title="Price (IDR)",
        margin=dict(l=10, r=120, t=50, b=10),
        legend=dict(orientation="v", x=1.01, y=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.12)")
    return fig


def mc_return_distribution(mc: dict) -> go.Figure:
    """Histogram of simulated terminal returns with VaR markers."""
    if not mc:
        return go.Figure()

    paths  = mc["paths"]
    last   = mc["last_price"]
    rets   = (paths[:, -1] / last - 1) * 100   # terminal % return

    fig = go.Figure()

    # Distribution bars
    fig.add_trace(go.Histogram(
        x=rets, nbinsx=60,
        marker_color=[
            _BUY if r > 0 else _SELL for r in rets
        ],
        name="Terminal returns",
        opacity=0.75,
        autobinx=False,
        xbins=dict(size=0.1),
    ))

    # VaR lines
    for level, label, color in [
        (mc["var_99"],  "VaR 99%",   "#FF5252"),
        (mc["var_95"],  "VaR 95%",   "#FF8A65"),
        (mc["expected_return"], "Expected", "#FFD54F"),
    ]:
        fig.add_vline(
            x=level, line=dict(color=color, dash="dash", width=1.5),
            annotation_text=f"{label}: {level:+.3f}%",
            annotation_position="top",
        )

    fig.add_vline(x=0, line=dict(color="white", dash="dot", width=1))

    fig.update_layout(
        template=_T,
        title="Terminal return distribution",
        height=300,
        xaxis_title="Return %",
        yaxis_title="Count",
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
