"""
Charts: builds Plotly figures from enriched DataFrames.
Returns go.Figure objects — the UI just calls st.plotly_chart().
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


_TEMPLATE = "plotly_dark"


def candlestick_with_indicators(df: pd.DataFrame, ticker: str) -> go.Figure:
    """4-panel chart: candlestick+MAs+BBands / Volume / RSI / MACD."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.50, 0.15, 0.20, 0.15],
        vertical_spacing=0.03,
        subplot_titles=(f"{ticker} — Price", "Volume", "RSI (14)", "MACD"),
    )

    # --- Candlestick ---
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ), row=1, col=1)

    # Bollinger Bands
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], name="BB Upper",
            line=dict(color="rgba(100,181,246,0.4)", width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], name="BB Lower",
            line=dict(color="rgba(100,181,246,0.4)", width=1),
            fill="tonexty", fillcolor="rgba(100,181,246,0.05)", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_mid"], name="BB Mid",
            line=dict(color="rgba(100,181,246,0.6)", width=1, dash="dot"), showlegend=False), row=1, col=1)

    # SMAs
    for col, color in [("SMA_20", "#FFD54F"), ("SMA_50", "#FF8A65")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col,
                line=dict(color=color, width=1.5)), row=1, col=1)

    # --- Volume ---
    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, showlegend=False), row=2, col=1)

    # --- RSI ---
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#CE93D8", width=1.5), showlegend=False), row=3, col=1)
        fig.add_hline(y=70, line=dict(color="red",    dash="dash", width=0.8), row=3, col=1)
        fig.add_hline(y=30, line=dict(color="green",  dash="dash", width=0.8), row=3, col=1)
        fig.add_hline(y=50, line=dict(color="gray",   dash="dot",  width=0.5), row=3, col=1)

    # --- MACD ---
    if "MACD" in df.columns:
        hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram",
            marker_color=hist_colors, showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
            line=dict(color="#80DEEA", width=1.5), showlegend=False), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal",
            line=dict(color="#FFCC80", width=1.5), showlegend=False), row=4, col=1)

    fig.update_layout(
        template=_TEMPLATE,
        height=700,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)")
    return fig


def watchlist_bar_chart(quotes: list[dict]) -> go.Figure:
    """Horizontal bar showing % change for each ticker."""
    sorted_q = sorted(quotes, key=lambda q: q["change_pct"])
    names  = [q["name"][:20] for q in sorted_q]
    values = [q["change_pct"] for q in sorted_q]
    colors = ["#ef5350" if v < 0 else "#26a69a" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        template=_TEMPLATE,
        height=350,
        margin=dict(l=10, r=60, t=20, b=10),
        xaxis_title="Change %",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.add_vline(x=0, line=dict(color="gray", dash="dot", width=0.8))
    return fig
