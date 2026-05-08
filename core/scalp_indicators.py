"""
Scalping indicators: fast, short-window indicators designed for 1m–5m charts.
Pure functions — no Streamlit references, no side effects.

Indicators added
    EMA_5, EMA_13       — micro-trend direction
    RSI_7               — short-window momentum
    VWAP                — intraday fair-value anchor
    Stoch_%K, Stoch_%D  — overbought / oversold oscillator
    ATR_7               — volatility for TP/SL sizing
    Momentum_3          — 3-bar price momentum
"""

from __future__ import annotations

import pandas as pd

from core.config import (
    SCALP_ATR_PERIOD,
    SCALP_EMA_FAST,
    SCALP_EMA_SLOW,
    SCALP_RSI_PERIOD,
    SCALP_STOCH_D,
    SCALP_STOCH_K,
    SCALP_VWAP_PERIOD,
)


def add_scalp_emas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[f"EMA_{SCALP_EMA_FAST}"] = df["Close"].ewm(span=SCALP_EMA_FAST, adjust=False).mean()
    df[f"EMA_{SCALP_EMA_SLOW}"] = df["Close"].ewm(span=SCALP_EMA_SLOW, adjust=False).mean()
    return df


def add_scalp_rsi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    delta    = df["Close"].diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / SCALP_RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / SCALP_RSI_PERIOD, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    df[f"RSI_{SCALP_RSI_PERIOD}"] = 100 - (100 / (1 + rs))
    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling VWAP over SCALP_VWAP_PERIOD bars (proxy for intraday VWAP)."""
    df = df.copy()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    tp_x_vol      = typical_price * df["Volume"]
    df["VWAP"] = (
        tp_x_vol.rolling(SCALP_VWAP_PERIOD).sum()
        / df["Volume"].rolling(SCALP_VWAP_PERIOD).sum()
    )
    return df


def add_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    """Stochastic oscillator (%K and %D smoothed)."""
    df       = df.copy()
    low_min  = df["Low"].rolling(SCALP_STOCH_K).min()
    high_max = df["High"].rolling(SCALP_STOCH_K).max()
    denom    = (high_max - low_min).replace(0, float("nan"))
    df["Stoch_K"] = 100 * (df["Close"] - low_min) / denom
    df["Stoch_D"] = df["Stoch_K"].rolling(SCALP_STOCH_D).mean()
    return df


def add_atr(df: pd.DataFrame) -> pd.DataFrame:
    """Average True Range for volatility-based TP/SL calculation."""
    df  = df.copy()
    hl  = df["High"] - df["Low"]
    hpc = (df["High"] - df["Close"].shift()).abs()
    lpc = (df["Low"]  - df["Close"].shift()).abs()
    tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    df[f"ATR_{SCALP_ATR_PERIOD}"] = tr.rolling(SCALP_ATR_PERIOD).mean()
    return df


def add_momentum(df: pd.DataFrame, period: int = 3) -> pd.DataFrame:
    """Short-window price momentum (% change over N bars)."""
    df = df.copy()
    df[f"Momentum_{period}"] = df["Close"].pct_change(period) * 100
    return df


def add_all_scalp_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Apply every scalping indicator in the correct order."""
    df = add_scalp_emas(df)
    df = add_scalp_rsi(df)
    df = add_vwap(df)
    df = add_stochastic(df)
    df = add_atr(df)
    df = add_momentum(df)
    return df
