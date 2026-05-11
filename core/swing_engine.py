"""
Swing Trade Engine
──────────────────
Six well-established swing trading strategies, each independently
generating a BUY / SELL / HOLD signal. All signals are then combined
into a confluence score and a final trade setup card.

────────────────────────────────────────────────────────────────────
STRATEGY 1 — ICHIMOKU CLOUD  (一目均衡表)
────────────────────────────────────────────────────────────────────
The most complete single-indicator system, widely used by
professional swing traders on Asian markets (very relevant for IDX).

Components:
  Tenkan-sen (9)     — short-term momentum (conversion line)
  Kijun-sen (26)     — medium-term momentum (base line)
  Senkou Span A      — fast cloud boundary (future, displaced +26)
  Senkou Span B (52) — slow cloud boundary (future, displaced +26)
  Chikou Span        — lagging line (close displaced −26)

BUY setup:  Price above cloud, Tenkan > Kijun, cloud is green (A > B)
SELL setup: Price below cloud, Tenkan < Kijun, cloud is red (B > A)

────────────────────────────────────────────────────────────────────
STRATEGY 2 — SUPERTREND
────────────────────────────────────────────────────────────────────
ATR-based trend-following indicator. Flips direction when price
crosses the ATR band. Extremely popular for swing entries/exits
because it gives a clear single line with a defined stop.

BUY:  Price closes above Supertrend line
SELL: Price closes below Supertrend line

────────────────────────────────────────────────────────────────────
STRATEGY 3 — FIBONACCI RETRACEMENT
────────────────────────────────────────────────────────────────────
Identifies the recent swing high and low, then plots key retracement
levels (23.6%, 38.2%, 50%, 61.8%, 78.6%). Price bouncing off these
levels in the direction of the trend is a classic swing entry.

BUY:  In uptrend + price near 38.2% or 61.8% retracement from swing low
SELL: In downtrend + price near 38.2% or 61.8% retracement from swing high

────────────────────────────────────────────────────────────────────
STRATEGY 4 — MACD SWING DIVERGENCE
────────────────────────────────────────────────────────────────────
Uses MACD histogram divergence (not just crossover) to catch swing
reversals before they happen. Bullish divergence: price makes lower
low but MACD histogram makes higher low.

BUY:  Bullish MACD divergence (momentum turning up before price)
SELL: Bearish MACD divergence (momentum turning down before price)

────────────────────────────────────────────────────────────────────
STRATEGY 5 — ELDER TRIPLE SCREEN
────────────────────────────────────────────────────────────────────
Dr. Alexander Elder's system: three screens (timeframes) must agree.
  Screen 1 (higher TF weekly EMA slope) — defines the tide/trend
  Screen 2 (oscillator on daily) — finds pullback entry
  Screen 3 (intraday breakout) — approximated by daily breakout above prior bar

BUY:  Weekly EMA rising + daily oscillator oversold (Stoch < 30) + price breaks prior high
SELL: Weekly EMA falling + daily oscillator overbought (Stoch > 70) + price breaks prior low

────────────────────────────────────────────────────────────────────
STRATEGY 6 — SUPPORT / RESISTANCE BREAKOUT with VOLUME CONFIRMATION
────────────────────────────────────────────────────────────────────
Classic swing: identify key S/R levels from swing highs/lows, then
trade breakouts/bounces confirmed by above-average volume.

BUY:  Price breaks above resistance with volume > 1.5× 20-bar avg
SELL: Price breaks below support with volume > 1.5× 20-bar avg
      OR price bounces off resistance with high volume (rejection)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from core.config import (
    BROKER_COMMISSION,
    ELDER_DAILY_STOCH,
    ELDER_STOCH_D,
    ELDER_WEEKLY_EMA,
    FIB_LEVELS,
    ICHI_DISPLACEMENT,
    ICHI_KIJUN,
    ICHI_SENKOU_B,
    ICHI_TENKAN,
    SELL_TAX_RATE,
    ST_ATR_PERIOD,
    ST_MULTIPLIER,
    SWING_MIN_CONFLUENCE,
)

Action = str   # "BUY" | "SELL" | "HOLD"
_COST  = (SELL_TAX_RATE + BROKER_COMMISSION * 2) * 100


def _last(s: pd.Series):
    return s.dropna().iloc[-1] if not s.dropna().empty else None


# ══════════════════════════════════════════════════════════════════
# INDICATORS
# ══════════════════════════════════════════════════════════════════

def compute_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    hi, lo, cl = df["High"], df["Low"], df["Close"]
    tenkan = (hi.rolling(ICHI_TENKAN).max() + lo.rolling(ICHI_TENKAN).min()) / 2
    kijun  = (hi.rolling(ICHI_KIJUN).max()  + lo.rolling(ICHI_KIJUN).min())  / 2
    span_a = ((tenkan + kijun) / 2).shift(ICHI_DISPLACEMENT)
    span_b = ((hi.rolling(ICHI_SENKOU_B).max() + lo.rolling(ICHI_SENKOU_B).min()) / 2).shift(ICHI_DISPLACEMENT)
    chikou = cl.shift(-ICHI_DISPLACEMENT)

    out = pd.DataFrame({
        "ichi_tenkan":  tenkan,
        "ichi_kijun":   kijun,
        "ichi_span_a":  span_a,
        "ichi_span_b":  span_b,
        "ichi_chikou":  chikou,
        "ichi_cloud_top":    span_a.combine(span_b, max),
        "ichi_cloud_bottom": span_a.combine(span_b, min),
    }, index=df.index)
    return out


def compute_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    hi, lo, cl = df["High"], df["Low"], df["Close"]
    hl   = hi - lo
    hpc  = (hi - cl.shift()).abs()
    lpc  = (lo - cl.shift()).abs()
    tr   = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
    atr  = tr.ewm(span=ST_ATR_PERIOD, adjust=False).mean()

    basic_upper = (hi + lo) / 2 + ST_MULTIPLIER * atr
    basic_lower = (hi + lo) / 2 - ST_MULTIPLIER * atr

    upper = basic_upper.copy()
    lower = basic_lower.copy()
    direction = pd.Series(1, index=df.index)
    supertrend = pd.Series(np.nan, index=df.index)

    for i in range(1, len(df)):
        # Upper band
        upper.iloc[i] = basic_upper.iloc[i] if (
            basic_upper.iloc[i] < upper.iloc[i-1] or cl.iloc[i-1] > upper.iloc[i-1]
        ) else upper.iloc[i-1]
        # Lower band
        lower.iloc[i] = basic_lower.iloc[i] if (
            basic_lower.iloc[i] > lower.iloc[i-1] or cl.iloc[i-1] < lower.iloc[i-1]
        ) else lower.iloc[i-1]
        # Direction
        if cl.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif cl.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        supertrend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

    return pd.DataFrame({
        "supertrend":       supertrend,
        "st_direction":     direction,   # +1 = bullish, -1 = bearish
        "st_upper":         upper,
        "st_lower":         lower,
    }, index=df.index)


def compute_fibonacci(df: pd.DataFrame, lookback: int = 50) -> dict:
    """Find most recent swing high/low and compute Fibonacci levels."""
    window = df.tail(lookback)
    swing_high = float(window["High"].max())
    swing_low  = float(window["Low"].min())
    diff = swing_high - swing_low

    levels = {
        f"fib_{int(l*1000)}": round(swing_high - diff * l, 2)
        for l in FIB_LEVELS
    }
    # Trend direction from linear regression
    slope = np.polyfit(range(len(window)), window["Close"].values, 1)[0]
    trend = "UP" if slope > 0 else "DOWN"

    return {
        "swing_high": swing_high,
        "swing_low":  swing_low,
        "levels":     levels,
        "trend":      trend,
        "diff":       diff,
    }


def compute_macd_divergence(df: pd.DataFrame) -> pd.DataFrame:
    cl   = df["Close"]
    ema12 = cl.ewm(span=12, adjust=False).mean()
    ema26 = cl.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    sig   = macd.ewm(span=9, adjust=False).mean()
    hist  = macd - sig

    # Detect divergence over last 10 bars
    div = pd.Series("NONE", index=df.index)
    for i in range(10, len(df)):
        price_window = cl.iloc[i-10:i+1]
        hist_window  = hist.iloc[i-10:i+1]
        price_low_now  = price_window.iloc[-1] <= price_window.min() * 1.002
        price_high_now = price_window.iloc[-1] >= price_window.max() * 0.998
        hist_low_now   = hist_window.iloc[-1] > hist_window.min()
        hist_high_now  = hist_window.iloc[-1] < hist_window.max()

        if price_low_now and hist_low_now:
            div.iloc[i] = "BULLISH"
        elif price_high_now and hist_high_now:
            div.iloc[i] = "BEARISH"

    return pd.DataFrame({
        "macd":      macd,
        "macd_sig":  sig,
        "macd_hist": hist,
        "macd_div":  div,
    }, index=df.index)


def compute_elder_screen(df: pd.DataFrame) -> pd.DataFrame:
    cl = df["Close"]

    # Screen 1: Weekly-proxy EMA trend
    weekly_ema = cl.ewm(span=ELDER_WEEKLY_EMA * 5, adjust=False).mean()  # ~65 bars ≈ 13 weeks
    ema_slope  = weekly_ema.diff(3)

    # Screen 2: Stochastic oscillator on current timeframe
    lo_min  = df["Low"].rolling(ELDER_DAILY_STOCH).min()
    hi_max  = df["High"].rolling(ELDER_DAILY_STOCH).max()
    stoch_k = 100 * (cl - lo_min) / (hi_max - lo_min).replace(0, np.nan)
    stoch_d = stoch_k.rolling(ELDER_STOCH_D).mean()

    # Screen 3: Breakout vs prior bar
    breakout_up   = cl > df["High"].shift(1)
    breakout_down = cl < df["Low"].shift(1)

    return pd.DataFrame({
        "elder_ema":        weekly_ema,
        "elder_ema_slope":  ema_slope,
        "elder_stoch_k":    stoch_k,
        "elder_stoch_d":    stoch_d,
        "elder_break_up":   breakout_up,
        "elder_break_down": breakout_down,
    }, index=df.index)


def compute_sr_breakout(df: pd.DataFrame, order: int = 5) -> dict:
    """Find key support/resistance levels from recent swing highs/lows."""
    hi  = df["High"].values
    lo  = df["Low"].values
    cl  = df["Close"]
    vol = df["Volume"]

    # Local maxima / minima
    peak_idx   = argrelextrema(hi, np.greater, order=order)[0]
    trough_idx = argrelextrema(lo, np.less,    order=order)[0]

    resistance_levels = sorted(set(hi[peak_idx].round(-1)),   reverse=True)[:5]
    support_levels    = sorted(set(lo[trough_idx].round(-1)),  reverse=True)[:5]

    # Volume confirmation
    vol_avg    = float(vol.rolling(20).mean().iloc[-1])
    cur_vol    = float(vol.iloc[-1])
    vol_surge  = cur_vol / vol_avg if vol_avg > 0 else 1.0
    cur_price  = float(cl.iloc[-1])
    prev_price = float(cl.iloc[-2]) if len(cl) > 1 else cur_price

    # Check if price just broke above nearest resistance or below nearest support
    nearest_res = min(resistance_levels, key=lambda r: abs(r - cur_price)) if resistance_levels else None
    nearest_sup = min(support_levels,    key=lambda s: abs(s - cur_price)) if support_levels   else None

    broke_resistance = (nearest_res and prev_price < nearest_res <= cur_price and vol_surge >= 1.5)
    broke_support    = (nearest_sup and prev_price > nearest_sup >= cur_price and vol_surge >= 1.5)
    rejected_resist  = (nearest_res and cur_price < nearest_res and prev_price > cur_price and vol_surge >= 1.3)

    return {
        "resistance_levels": resistance_levels,
        "support_levels":    support_levels,
        "nearest_resistance": nearest_res,
        "nearest_support":    nearest_sup,
        "vol_surge":          round(vol_surge, 2),
        "broke_resistance":   broke_resistance,
        "broke_support":      broke_support,
        "rejected_resistance": rejected_resist,
        "cur_price":           cur_price,
    }


# ══════════════════════════════════════════════════════════════════
# SIGNAL GENERATORS (one per strategy)
# ══════════════════════════════════════════════════════════════════

def _ichi_signal(df: pd.DataFrame, ichi: pd.DataFrame) -> dict:
    price     = float(df["Close"].iloc[-1])
    cloud_top = _last(ichi["ichi_cloud_top"])
    cloud_bot = _last(ichi["ichi_cloud_bottom"])
    tenkan    = _last(ichi["ichi_tenkan"])
    kijun     = _last(ichi["ichi_kijun"])
    span_a    = _last(ichi["ichi_span_a"])
    span_b    = _last(ichi["ichi_span_b"])

    if any(v is None for v in [cloud_top, cloud_bot, tenkan, kijun]):
        return {"action": "HOLD", "reason": "Ichimoku: insufficient data", "strength": 0}

    above_cloud = price > cloud_top
    below_cloud = price < cloud_bot
    bullish_tk  = tenkan > kijun
    bearish_tk  = tenkan < kijun
    green_cloud = (span_a or 0) >= (span_b or 0)

    if above_cloud and bullish_tk and green_cloud:
        return {"action": "BUY",  "reason": f"Ichimoku: price above cloud, TK bullish, green cloud", "strength": 3}
    if above_cloud and bullish_tk:
        return {"action": "BUY",  "reason": f"Ichimoku: price above cloud, TK bullish", "strength": 2}
    if below_cloud and bearish_tk and not green_cloud:
        return {"action": "SELL", "reason": f"Ichimoku: price below cloud, TK bearish, red cloud", "strength": 3}
    if below_cloud and bearish_tk:
        return {"action": "SELL", "reason": f"Ichimoku: price below cloud, TK bearish", "strength": 2}
    return {"action": "HOLD", "reason": "Ichimoku: price inside cloud or mixed", "strength": 0}


def _supertrend_signal(df: pd.DataFrame, st: pd.DataFrame) -> dict:
    direction = _last(st["st_direction"])
    st_line   = _last(st["supertrend"])
    price     = float(df["Close"].iloc[-1])
    if direction is None:
        return {"action": "HOLD", "reason": "Supertrend: no data", "strength": 0}
    if direction == 1:
        return {"action": "BUY",  "reason": f"Supertrend: bullish, support at Rp {st_line:,.0f}", "strength": 2}
    return {"action": "SELL", "reason": f"Supertrend: bearish, resistance at Rp {st_line:,.0f}", "strength": 2}


def _fibonacci_signal(df: pd.DataFrame, fib: dict) -> dict:
    price  = float(df["Close"].iloc[-1])
    trend  = fib["trend"]
    levels = fib["levels"]
    diff   = fib["diff"]
    if diff == 0:
        return {"action": "HOLD", "reason": "Fibonacci: no swing detected", "strength": 0}

    # Find nearest fib level
    level_prices = list(levels.values())
    nearest      = min(level_prices, key=lambda l: abs(l - price))
    dist_pct     = abs(nearest - price) / price * 100
    level_name   = [k for k, v in levels.items() if v == nearest][0]

    key_levels = ["fib_382", "fib_500", "fib_618"]   # classic retracement entries

    if trend == "UP" and dist_pct < 1.5 and level_name in key_levels:
        return {"action": "BUY",  "reason": f"Fibonacci: uptrend, near {level_name.replace('fib_','')} retracement ({dist_pct:.2f}% away)", "strength": 2}
    if trend == "DOWN" and dist_pct < 1.5 and level_name in key_levels:
        return {"action": "SELL", "reason": f"Fibonacci: downtrend, near {level_name.replace('fib_','')} retracement ({dist_pct:.2f}% away)", "strength": 2}
    return {"action": "HOLD", "reason": f"Fibonacci: not near key level (closest {dist_pct:.2f}% away)", "strength": 0}


def _macd_div_signal(macd_df: pd.DataFrame) -> dict:
    div = _last(macd_df["macd_div"])
    hist = _last(macd_df["macd_hist"])
    if div == "BULLISH":
        return {"action": "BUY",  "reason": f"MACD: bullish divergence — momentum turning before price", "strength": 2}
    if div == "BEARISH":
        return {"action": "SELL", "reason": f"MACD: bearish divergence — momentum fading", "strength": 2}
    # Fallback: simple histogram direction
    if hist is not None and hist > 0:
        return {"action": "BUY",  "reason": f"MACD: histogram positive ({hist:.4f})", "strength": 1}
    if hist is not None and hist < 0:
        return {"action": "SELL", "reason": f"MACD: histogram negative ({hist:.4f})", "strength": 1}
    return {"action": "HOLD", "reason": "MACD: neutral", "strength": 0}


def _elder_signal(elder: pd.DataFrame) -> dict:
    slope   = _last(elder["elder_ema_slope"])
    stoch_k = _last(elder["elder_stoch_k"])
    break_u = bool(elder["elder_break_up"].iloc[-1])
    break_d = bool(elder["elder_break_down"].iloc[-1])
    if slope is None or stoch_k is None:
        return {"action": "HOLD", "reason": "Elder: insufficient data", "strength": 0}

    uptrend   = slope > 0
    downtrend = slope < 0

    if uptrend and stoch_k < 30 and break_u:
        return {"action": "BUY",  "reason": f"Elder Triple Screen: tide up, stoch oversold ({stoch_k:.0f}), bar breakout ✓", "strength": 3}
    if uptrend and stoch_k < 40:
        return {"action": "BUY",  "reason": f"Elder Triple Screen: tide up, stoch pulling back ({stoch_k:.0f})", "strength": 2}
    if downtrend and stoch_k > 70 and break_d:
        return {"action": "SELL", "reason": f"Elder Triple Screen: tide down, stoch overbought ({stoch_k:.0f}), bar breakdown ✓", "strength": 3}
    if downtrend and stoch_k > 60:
        return {"action": "SELL", "reason": f"Elder Triple Screen: tide down, stoch elevated ({stoch_k:.0f})", "strength": 2}
    return {"action": "HOLD", "reason": f"Elder: no confluence (slope={slope:.2f}, stoch={stoch_k:.0f})", "strength": 0}


def _sr_signal(sr: dict) -> dict:
    if sr["broke_resistance"]:
        return {"action": "BUY",  "reason": f"S/R Breakout: closed above resistance with {sr['vol_surge']:.1f}× vol surge", "strength": 3}
    if sr["broke_support"]:
        return {"action": "SELL", "reason": f"S/R Breakdown: closed below support with {sr['vol_surge']:.1f}× vol surge", "strength": 3}
    if sr["rejected_resistance"]:
        return {"action": "SELL", "reason": f"S/R Rejection: failed at resistance with high volume", "strength": 2}
    return {"action": "HOLD", "reason": "S/R: no confirmed breakout/breakdown", "strength": 0}


# ══════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════

def run_swing_analysis(df: pd.DataFrame) -> dict:
    """
    Run all 6 strategies and return a comprehensive result dict.
    """
    ichi  = compute_ichimoku(df)
    st_df = compute_supertrend(df)
    fib   = compute_fibonacci(df)
    macd  = compute_macd_divergence(df)
    elder = compute_elder_screen(df)
    sr    = compute_sr_breakout(df)

    signals = {
        "Ichimoku Cloud":         _ichi_signal(df, ichi),
        "Supertrend":             _supertrend_signal(df, st_df),
        "Fibonacci Retracement":  _fibonacci_signal(df, fib),
        "MACD Divergence":        _macd_div_signal(macd),
        "Elder Triple Screen":    _elder_signal(elder),
        "S/R Breakout":           _sr_signal(sr),
    }

    # Confluence vote weighted by strength
    buy_score  = sum(s["strength"] for s in signals.values() if s["action"] == "BUY")
    sell_score = sum(s["strength"] for s in signals.values() if s["action"] == "SELL")
    buy_count  = sum(1 for s in signals.values() if s["action"] == "BUY")
    sell_count = sum(1 for s in signals.values() if s["action"] == "SELL")
    max_score  = max(buy_score, sell_score)
    total_possible = sum(s["strength"] for s in signals.values()) or 1

    if buy_count >= SWING_MIN_CONFLUENCE and buy_score > sell_score:
        verdict = "BUY"
    elif sell_count >= SWING_MIN_CONFLUENCE and sell_score > buy_score:
        verdict = "SELL"
    else:
        verdict = "WAIT"

    confidence = max_score / total_possible

    # Trade setup levels
    price = float(df["Close"].iloc[-1])
    atr_col = df["High"].sub(df["Low"]).ewm(span=ST_ATR_PERIOD).mean().iloc[-1]

    if verdict == "BUY":
        stop_loss    = round(price - atr_col * 2, 0)
        target_1     = round(price + atr_col * 2, 0)
        target_2     = round(price + atr_col * 4, 0)
        target_3     = round(price + atr_col * 6, 0)
    elif verdict == "SELL":
        stop_loss    = round(price + atr_col * 2, 0)
        target_1     = round(price - atr_col * 2, 0)
        target_2     = round(price - atr_col * 4, 0)
        target_3     = round(price - atr_col * 6, 0)
    else:
        stop_loss = target_1 = target_2 = target_3 = price

    sl_pct  = abs(price - stop_loss) / price * 100
    t1_pct  = abs(price - target_1)  / price * 100
    rr      = t1_pct / sl_pct if sl_pct > 0 else 0

    # Enrich df with all indicators
    enriched = df.copy()
    for col in ichi.columns:
        enriched[col] = ichi[col]
    for col in st_df.columns:
        enriched[col] = st_df[col]
    for col in macd.columns:
        enriched[col] = macd[col]
    for col in elder.columns:
        enriched[col] = elder[col]

    return {
        "enriched_df": enriched,
        "signals":     signals,
        "verdict":     verdict,
        "confidence":  round(confidence, 3),
        "buy_count":   buy_count,
        "sell_count":  sell_count,
        "buy_score":   buy_score,
        "sell_score":  sell_score,
        "price":       price,
        "stop_loss":   stop_loss,
        "target_1":    target_1,
        "target_2":    target_2,
        "target_3":    target_3,
        "sl_pct":      round(sl_pct, 2),
        "t1_pct":      round(t1_pct, 2),
        "risk_reward": round(rr, 2),
        "atr":         round(float(atr_col), 2),
        "fib":         fib,
        "sr":          sr,
        "cost_pct":    round(_COST, 3),
    }
