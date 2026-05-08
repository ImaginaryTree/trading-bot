"""
Indicators: computes technical indicators on an OHLCV DataFrame.
Pure functions — no side effects, no Streamlit references.
"""

from __future__ import annotations

import pandas as pd

from core.config import BB_PERIOD, BB_STD, MA_LONG, MA_SHORT, RSI_PERIOD


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA short and long columns."""
    df = df.copy()
    df[f"SMA_{MA_SHORT}"] = df["Close"].rolling(MA_SHORT).mean()
    df[f"SMA_{MA_LONG}"] = df["Close"].rolling(MA_LONG).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.DataFrame:
    """Add RSI column using Wilder's smoothing."""
    df = df.copy()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = BB_PERIOD,
    std_dev: float = BB_STD,
) -> pd.DataFrame:
    """Add Bollinger Band columns (upper, mid, lower)."""
    df = df.copy()
    mid = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    df["BB_upper"] = mid + std_dev * std
    df["BB_mid"] = mid
    df["BB_lower"] = mid - std_dev * std
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Add MACD line, signal line, and histogram."""
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Apply every indicator in one call."""
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_bollinger_bands(df)
    df = add_macd(df)
    return df
