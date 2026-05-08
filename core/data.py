"""
Data layer: fetches OHLCV data from Yahoo Finance for IDX tickers.
All functions return plain DataFrames — no Streamlit dependencies here.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from core.config import IDX_WATCHLIST

logger = logging.getLogger(__name__)


def fetch_ohlcv(
    ticker: str,
    period: str = "1d",
    interval: str = "5m",
) -> pd.DataFrame:
    """Download OHLCV data for a single ticker.

    Returns an empty DataFrame on failure so callers never crash.
    """
    try:
        raw = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if raw.empty:
            logger.warning("No data returned for %s", ticker)
            return pd.DataFrame()

        df = raw.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.index = pd.to_datetime(df.index)
        df.index.name = "datetime"
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df

    except Exception as exc:
        logger.error("fetch_ohlcv failed for %s: %s", ticker, exc)
        return pd.DataFrame()


def fetch_quote(ticker: str) -> dict:
    """Return a lightweight quote snapshot (last price, change, etc.)."""
    try:
        info = yf.Ticker(ticker).fast_info
        prev_close = getattr(info, "previous_close", None) or 0.0
        last_price = getattr(info, "last_price", None) or 0.0
        change = last_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        return {
            "ticker": ticker,
            "name": IDX_WATCHLIST.get(ticker, ticker),
            "last_price": last_price,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "volume": getattr(info, "three_month_average_volume", 0) or 0,
            "market_cap": getattr(info, "market_cap", 0) or 0,
            "fetched_at": datetime.now(),
        }
    except Exception as exc:
        logger.error("fetch_quote failed for %s: %s", ticker, exc)
        return {
            "ticker": ticker,
            "name": IDX_WATCHLIST.get(ticker, ticker),
            "last_price": 0.0,
            "prev_close": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": 0,
            "market_cap": 0,
            "fetched_at": datetime.now(),
        }


def fetch_watchlist_quotes(tickers: Optional[list[str]] = None) -> list[dict]:
    """Fetch quotes for every ticker in the watchlist."""
    tickers = tickers or list(IDX_WATCHLIST.keys())
    return [fetch_quote(t) for t in tickers]
