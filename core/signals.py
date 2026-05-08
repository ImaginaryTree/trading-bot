"""
Signals: generates BUY / SELL / HOLD signals from indicator columns.
Returns a plain dict so the UI layer can render it however it likes.
"""

from __future__ import annotations

import pandas as pd


SignalResult = dict  # {"signal": str, "reasons": list[str], "confidence": float}


def _latest(df: pd.DataFrame, col: str):
    """Safe last-row access."""
    return df[col].dropna().iloc[-1] if col in df.columns and not df[col].dropna().empty else None


def ma_crossover_signal(df: pd.DataFrame) -> SignalResult:
    """Golden / death cross between the two SMAs."""
    short_col = [c for c in df.columns if c.startswith("SMA_") and int(c.split("_")[1]) < 30]
    long_col  = [c for c in df.columns if c.startswith("SMA_") and int(c.split("_")[1]) >= 30]
    if not short_col or not long_col:
        return {"signal": "HOLD", "reasons": ["Need SMA columns"], "confidence": 0.0}

    short_val = _latest(df, short_col[0])
    long_val  = _latest(df, long_col[0])
    if short_val is None or long_val is None:
        return {"signal": "HOLD", "reasons": ["Insufficient data"], "confidence": 0.0}

    if short_val > long_val:
        return {"signal": "BUY", "reasons": [f"SMA{short_col[0].split('_')[1]} > SMA{long_col[0].split('_')[1]} (golden cross)"], "confidence": 0.65}
    return {"signal": "SELL", "reasons": [f"SMA{short_col[0].split('_')[1]} < SMA{long_col[0].split('_')[1]} (death cross)"], "confidence": 0.55}


def rsi_signal(df: pd.DataFrame) -> SignalResult:
    """Oversold / overbought from RSI."""
    rsi = _latest(df, "RSI")
    if rsi is None:
        return {"signal": "HOLD", "reasons": ["RSI not available"], "confidence": 0.0}
    if rsi < 30:
        return {"signal": "BUY",  "reasons": [f"RSI oversold ({rsi:.1f})"], "confidence": 0.70}
    if rsi > 70:
        return {"signal": "SELL", "reasons": [f"RSI overbought ({rsi:.1f})"], "confidence": 0.70}
    return {"signal": "HOLD", "reasons": [f"RSI neutral ({rsi:.1f})"], "confidence": 0.50}


def bollinger_signal(df: pd.DataFrame) -> SignalResult:
    """Price outside Bollinger Bands."""
    price  = _latest(df, "Close")
    upper  = _latest(df, "BB_upper")
    lower  = _latest(df, "BB_lower")
    if None in (price, upper, lower):
        return {"signal": "HOLD", "reasons": ["Bollinger data missing"], "confidence": 0.0}
    if price < lower:
        return {"signal": "BUY",  "reasons": ["Price below lower Bollinger Band"], "confidence": 0.65}
    if price > upper:
        return {"signal": "SELL", "reasons": ["Price above upper Bollinger Band"], "confidence": 0.65}
    return {"signal": "HOLD", "reasons": ["Price inside Bollinger Bands"], "confidence": 0.50}


def macd_signal(df: pd.DataFrame) -> SignalResult:
    """MACD histogram direction."""
    hist = _latest(df, "MACD_hist")
    macd = _latest(df, "MACD")
    if None in (hist, macd):
        return {"signal": "HOLD", "reasons": ["MACD data missing"], "confidence": 0.0}
    if macd > 0 and hist > 0:
        return {"signal": "BUY",  "reasons": [f"MACD bullish (hist={hist:.4f})"], "confidence": 0.60}
    if macd < 0 and hist < 0:
        return {"signal": "SELL", "reasons": [f"MACD bearish (hist={hist:.4f})"], "confidence": 0.60}
    return {"signal": "HOLD", "reasons": ["MACD mixed"], "confidence": 0.50}


def aggregate_signals(df: pd.DataFrame) -> dict:
    """Combine all signals into a majority-vote recommendation."""
    signals = {
        "MA Crossover": ma_crossover_signal(df),
        "RSI":          rsi_signal(df),
        "Bollinger":    bollinger_signal(df),
        "MACD":         macd_signal(df),
    }

    votes: dict[str, float] = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
    for result in signals.values():
        votes[result["signal"]] += result["confidence"]

    recommendation = max(votes, key=lambda k: votes[k])
    total = sum(votes.values()) or 1
    confidence = votes[recommendation] / total

    return {
        "recommendation": recommendation,
        "confidence": round(confidence, 2),
        "breakdown": signals,
        "votes": votes,
    }
