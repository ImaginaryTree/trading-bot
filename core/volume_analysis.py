"""
Volume Analysis Engine
──────────────────────
Five orthogonal methods to detect whether large/informed players
(institutions, "bandar") are accumulating or distributing a stock,
using only OHLCV data.

────────────────────────────────────────────────────────────────────
METHOD 1 — VPIN  (Volume-Synchronized Probability of Informed Trading)
────────────────────────────────────────────────────────────────────
Easley, López de Prado & O'Hara (2012). Splits volume into fixed-
size buckets, computes buy/sell imbalance per bucket, then takes a
rolling average. High VPIN = informed (non-random) order flow.
  • VPIN < 0.25  → balanced, uninformed flow (retail noise)
  • VPIN > 0.50  → directional, likely informed flow
  • VPIN > 0.70  → strongly informed — someone knows something

────────────────────────────────────────────────────────────────────
METHOD 2 — EFFORT vs RESULT  (Wyckoff's core principle)
────────────────────────────────────────────────────────────────────
If volume (effort) is abnormally high but the resulting price move
is small, a large player is absorbing the flow — they are on the
OTHER side of every trade, quietly accumulating or distributing.
  • High effort + small result on down bar → ACCUMULATION signal
  • High effort + small result on up bar   → DISTRIBUTION signal
  • High effort + large result             → Genuine breakout

────────────────────────────────────────────────────────────────────
METHOD 3 — WYCKOFF PHASE DETECTOR
────────────────────────────────────────────────────────────────────
Uses price range, volume trend, and position within the range to
classify each bar into a Wyckoff phase:
  ACCUMULATION — low volatility range, volume declining, price at lows
  MARKUP       — rising price with expanding volume
  DISTRIBUTION — low volatility range, volume declining, price at highs
  MARKDOWN     — falling price with expanding volume
  SPRING       — sharp low-volume dip below range support (trap)
  UTAD         — sharp high-volume spike above range resistance (trap)

────────────────────────────────────────────────────────────────────
METHOD 4 — VOLUME PROFILE
────────────────────────────────────────────────────────────────────
Bins all traded volume by price level. The Point of Control (POC)
is the price with maximum traded volume — this is where the most
institutional interest is concentrated. High-volume nodes (HVN)
act as support/resistance. Low-volume nodes (LVN) are fast-move zones.

────────────────────────────────────────────────────────────────────
METHOD 5 — CHAIKIN MONEY FLOW + OBV DIVERGENCE
────────────────────────────────────────────────────────────────────
CMF = rolling sum of Money Flow Volume / rolling sum of Volume.
Positive CMF = buying pressure, negative = selling pressure.
OBV divergence: price making new highs but OBV falling = distribution.
Price making new lows but OBV rising = accumulation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from core.config import (
    CMF_WINDOW,
    EVR_THRESHOLD,
    EVR_WINDOW,
    FLOW_IMBALANCE_STRONG,
    SMART_SCORE_ACCUMULATE,
    SMART_SCORE_DISTRIBUTE,
    VP_BINS,
    VPIN_BUCKET_SIZE_FACTOR,
    VPIN_WINDOW,
    WYCKOFF_RANGE_THRESHOLD,
    WYCKOFF_WINDOW,
)


# ── Shared buy/sell fraction (reuse BVC blend from quant_engine) ──────────────

def _buy_frac_series(df: pd.DataFrame) -> pd.Series:
    """Blended buy fraction: tick rule + BVC + candle body."""
    # Tick rule
    chg  = df["Close"].diff()
    tick = pd.Series(0.5, index=df.index)
    tick[chg > 0] = 1.0
    tick[chg < 0] = 0.0

    # BVC
    log_ret = np.log(df["Close"] / df["Close"].shift(1))
    sigma   = log_ret.rolling(20).std().replace(0, np.nan)
    bvc     = (log_ret / sigma).apply(
        lambda z: float(scipy_stats.norm.cdf(z)) if not np.isnan(z) else 0.5
    )

    # Candle body
    hl = (df["High"] - df["Low"]).replace(0, np.nan)
    body = ((df["Close"] - df["Low"]) / hl).fillna(0.5)

    return ((tick + bvc + body) / 3.0).clip(0, 1)


# ══════════════════════════════════════════════════════════════════
# METHOD 1: VPIN
# ══════════════════════════════════════════════════════════════════

def compute_vpin(df: pd.DataFrame) -> pd.Series:
    """
    Bar-level VPIN approximation using fixed-fraction volume buckets.
    Returns a Series aligned to df.index (NaN for early rows).
    """
    buy_frac  = _buy_frac_series(df)
    buy_vol   = buy_frac * df["Volume"]
    sell_vol  = (1 - buy_frac) * df["Volume"]
    imbalance = (buy_vol - sell_vol).abs()

    avg_vol   = df["Volume"].rolling(VPIN_WINDOW).mean()
    bucket_sz = avg_vol * VPIN_BUCKET_SIZE_FACTOR

    # Rolling VPIN: mean absolute imbalance / mean bucket size
    rolling_imb = imbalance.rolling(VPIN_WINDOW).mean()
    rolling_bkt = bucket_sz.rolling(VPIN_WINDOW).mean().replace(0, np.nan)

    vpin = (rolling_imb / rolling_bkt).clip(0, 1)
    return vpin.rename("VPIN")


# ══════════════════════════════════════════════════════════════════
# METHOD 2: EFFORT vs RESULT
# ══════════════════════════════════════════════════════════════════

def compute_effort_vs_result(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame with columns:
        effort          — normalised volume (z-score)
        result          — normalised bar range (z-score)
        evr_ratio       — effort / |result|  (high = absorption)
        evr_signal      — 'ABSORPTION_BUY' | 'ABSORPTION_SELL' | 'BREAKOUT' | 'NORMAL'
        evr_anomaly     — bool: True when clearly anomalous
    """
    out = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    bar_range = df["High"] - df["Low"]
    bar_move  = (df["Close"] - df["Open"]).abs()

    # Z-scores relative to rolling window
    vol_mean  = df["Volume"].rolling(EVR_WINDOW).mean()
    vol_std   = df["Volume"].rolling(EVR_WINDOW).std().replace(0, np.nan)
    rng_mean  = bar_range.rolling(EVR_WINDOW).mean()
    rng_std   = bar_range.rolling(EVR_WINDOW).std().replace(0, np.nan)

    out["effort"]  = (df["Volume"] - vol_mean) / vol_std
    out["result"]  = (bar_range - rng_mean) / rng_std
    out["evr_ratio"] = out["effort"] / (out["result"].abs() + 0.01)

    # Classify each bar
    signals = []
    for _, row in out.iterrows():
        e, r = row["effort"], row["result"]
        is_up = row["Close"] >= row["Open"]
        if e > EVR_THRESHOLD and r < 0:
            # High effort, small result → absorption
            sig = "ABSORPTION_BUY" if is_up else "ABSORPTION_SELL"
        elif e > EVR_THRESHOLD and r > EVR_THRESHOLD:
            sig = "BREAKOUT"
        else:
            sig = "NORMAL"
        signals.append(sig)

    out["evr_signal"]  = signals
    out["evr_anomaly"] = out["evr_signal"] != "NORMAL"
    return out[["effort", "result", "evr_ratio", "evr_signal", "evr_anomaly"]]


# ══════════════════════════════════════════════════════════════════
# METHOD 3: WYCKOFF PHASE DETECTOR
# ══════════════════════════════════════════════════════════════════

_PHASES = ["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN", "SPRING", "UTAD", "UNCLEAR"]

def compute_wyckoff_phases(df: pd.DataFrame) -> pd.Series:
    """
    Classify each bar with a Wyckoff phase label.
    Uses a rolling window of WYCKOFF_WINDOW bars for context.
    """
    phases = pd.Series("UNCLEAR", index=df.index)
    n = len(df)

    for i in range(WYCKOFF_WINDOW, n):
        window = df.iloc[i - WYCKOFF_WINDOW: i + 1]
        close  = window["Close"]
        vol    = window["Volume"]
        hi     = window["High"]
        lo     = window["Low"]

        price_range_pct = (hi.max() - lo.min()) / lo.min() if lo.min() > 0 else 0
        vol_trend  = np.polyfit(range(len(vol)), vol.values, 1)[0]
        price_trend = np.polyfit(range(len(close)), close.values, 1)[0]

        cur_close  = close.iloc[-1]
        range_low  = lo.min()
        range_high = hi.max()
        range_size = range_high - range_low
        pos_in_range = (cur_close - range_low) / range_size if range_size > 0 else 0.5

        in_range = price_range_pct < WYCKOFF_RANGE_THRESHOLD
        cur_vol  = vol.iloc[-1]
        avg_vol  = vol.mean()
        low_vol  = cur_vol < avg_vol * 0.75
        high_vol = cur_vol > avg_vol * 1.5

        prev_close = close.iloc[-2] if len(close) > 1 else cur_close
        bar_drop   = (prev_close - cur_close) / prev_close if prev_close > 0 else 0
        bar_rise   = (cur_close - prev_close) / prev_close if prev_close > 0 else 0

        # Spring: brief dip below range low on low volume
        if cur_close < range_low * 1.005 and low_vol and bar_drop > 0.005:
            phases.iloc[i] = "SPRING"
        # UTAD: brief spike above range high on high volume
        elif cur_close > range_high * 0.995 and high_vol and bar_rise > 0.005:
            phases.iloc[i] = "UTAD"
        # Accumulation: in range, at lows, volume declining
        elif in_range and pos_in_range < 0.4 and vol_trend < 0:
            phases.iloc[i] = "ACCUMULATION"
        # Distribution: in range, at highs, volume declining
        elif in_range and pos_in_range > 0.6 and vol_trend < 0:
            phases.iloc[i] = "DISTRIBUTION"
        # Markup: rising price, expanding volume
        elif price_trend > 0 and vol_trend > 0:
            phases.iloc[i] = "MARKUP"
        # Markdown: falling price, expanding volume
        elif price_trend < 0 and vol_trend > 0:
            phases.iloc[i] = "MARKDOWN"
        else:
            phases.iloc[i] = "UNCLEAR"

    return phases.rename("wyckoff_phase")


# ══════════════════════════════════════════════════════════════════
# METHOD 4: VOLUME PROFILE
# ══════════════════════════════════════════════════════════════════

def compute_volume_profile(df: pd.DataFrame) -> dict:
    """
    Returns a dict:
        bins        — array of price levels (bin edges)
        vol_by_price — array of volume at each price level
        poc         — Point of Control price (max volume level)
        poc_vol     — volume at POC
        hvn         — list of High-Volume Node prices (top 20%)
        lvn         — list of Low-Volume Node prices (bottom 20%)
        value_area_high — upper bound of value area (70% of volume)
        value_area_low  — lower bound of value area
    """
    lo, hi = df["Low"].min(), df["High"].max()
    bins   = np.linspace(lo, hi, VP_BINS + 1)
    centers = (bins[:-1] + bins[1:]) / 2
    vol_by_price = np.zeros(VP_BINS)

    for _, row in df.iterrows():
        # Distribute bar volume uniformly across its price range
        b_lo = max(row["Low"],  lo)
        b_hi = min(row["High"], hi)
        if b_hi <= b_lo:
            continue
        bar_bins = np.searchsorted(bins, [b_lo, b_hi])
        start, end = max(0, bar_bins[0] - 1), min(VP_BINS, bar_bins[1])
        if end > start:
            vol_per_bin = row["Volume"] / (end - start)
            vol_by_price[start:end] += vol_per_bin

    poc_idx = int(np.argmax(vol_by_price))
    poc     = float(centers[poc_idx])
    poc_vol = float(vol_by_price[poc_idx])

    # Value area: bins containing 70% of total volume, expanding from POC
    total_vol = vol_by_price.sum()
    target    = total_vol * 0.70
    va_lo_idx, va_hi_idx = poc_idx, poc_idx
    accumulated = vol_by_price[poc_idx]
    while accumulated < target and (va_lo_idx > 0 or va_hi_idx < VP_BINS - 1):
        add_lo = vol_by_price[va_lo_idx - 1] if va_lo_idx > 0 else 0
        add_hi = vol_by_price[va_hi_idx + 1] if va_hi_idx < VP_BINS - 1 else 0
        if add_hi >= add_lo and va_hi_idx < VP_BINS - 1:
            va_hi_idx += 1
            accumulated += add_hi
        elif va_lo_idx > 0:
            va_lo_idx -= 1
            accumulated += add_lo
        else:
            break

    threshold_hi = np.percentile(vol_by_price, 80)
    threshold_lo = np.percentile(vol_by_price, 20)

    return {
        "bins":             bins,
        "centers":          centers,
        "vol_by_price":     vol_by_price,
        "poc":              poc,
        "poc_vol":          poc_vol,
        "hvn":              centers[vol_by_price >= threshold_hi].tolist(),
        "lvn":              centers[vol_by_price <= threshold_lo].tolist(),
        "value_area_high":  float(centers[va_hi_idx]),
        "value_area_low":   float(centers[va_lo_idx]),
    }


# ══════════════════════════════════════════════════════════════════
# METHOD 5: CHAIKIN MONEY FLOW + OBV DIVERGENCE
# ══════════════════════════════════════════════════════════════════

def compute_cmf_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame with:
        OBV             — On-Balance Volume
        CMF             — Chaikin Money Flow
        cmf_signal      — 'BUYING' | 'SELLING' | 'NEUTRAL'
        obv_divergence  — 'BULLISH_DIV' | 'BEARISH_DIV' | 'NONE'
    """
    out = pd.DataFrame(index=df.index)

    # OBV
    direction = np.sign(df["Close"].diff().fillna(0))
    out["OBV"] = (direction * df["Volume"]).cumsum()

    # CMF: Money Flow Multiplier × Volume, then rolling sum / rolling vol
    hl   = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm  = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / hl
    mfv  = mfm * df["Volume"]
    out["CMF"] = (
        mfv.rolling(CMF_WINDOW).sum()
        / df["Volume"].rolling(CMF_WINDOW).sum().replace(0, np.nan)
    )

    out["cmf_signal"] = "NEUTRAL"
    out.loc[out["CMF"] >  0.05, "cmf_signal"] = "BUYING"
    out.loc[out["CMF"] < -0.05, "cmf_signal"] = "SELLING"

    # OBV divergence over a 20-bar lookback
    div = []
    for i in range(20, len(df)):
        price_now  = df["Close"].iloc[i]
        price_back = df["Close"].iloc[i - 20]
        obv_now    = out["OBV"].iloc[i]
        obv_back   = out["OBV"].iloc[i - 20]
        if price_now < price_back and obv_now > obv_back:
            div.append("BULLISH_DIV")    # price falling but OBV rising → accumulation
        elif price_now > price_back and obv_now < obv_back:
            div.append("BEARISH_DIV")    # price rising but OBV falling → distribution
        else:
            div.append("NONE")
    out["obv_divergence"] = ["NONE"] * 20 + div

    return out


# ══════════════════════════════════════════════════════════════════
# AGGREGATE: Smart Money Score
# ══════════════════════════════════════════════════════════════════

def compute_smart_money_score(
    df: pd.DataFrame,
    vpin: pd.Series,
    evr: pd.DataFrame,
    phases: pd.Series,
    cmf_obv: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combines all signals into a rolling Smart Money Score in [-1, +1]:
      +1 = strong accumulation evidence (smart money buying)
      -1 = strong distribution evidence (smart money selling)
       0 = no clear edge

    Each method contributes a component score:
        VPIN component   — high VPIN = informed flow (directional, sign from CMF)
        EVR component    — absorption signals
        Wyckoff component — phase-based directional vote
        CMF component    — money flow direction
        OBV div component — divergence confirmation
    """
    n   = len(df)
    scores = pd.Series(0.0, index=df.index)

    for i in range(WYCKOFF_WINDOW, n):
        row_vpin  = vpin.iloc[i]
        row_evr   = evr.iloc[i]
        row_phase = phases.iloc[i]
        row_cmf   = cmf_obv.iloc[i]

        score = 0.0

        # VPIN: contribution is signed by CMF direction
        if not np.isnan(row_vpin):
            cmf_dir = 1 if row_cmf.get("cmf_signal") == "BUYING" else (
                      -1 if row_cmf.get("cmf_signal") == "SELLING" else 0)
            score += row_vpin * cmf_dir * 0.25

        # EVR
        evr_sig = row_evr.get("evr_signal", "NORMAL")
        if evr_sig == "ABSORPTION_BUY":   score += 0.20
        elif evr_sig == "ABSORPTION_SELL": score -= 0.20
        elif evr_sig == "BREAKOUT":
            chg = df["Close"].iloc[i] - df["Close"].iloc[i - 1]
            score += 0.10 if chg > 0 else -0.10

        # Wyckoff
        phase_scores = {
            "ACCUMULATION": 0.25, "SPRING": 0.30,
            "MARKUP": 0.15,
            "DISTRIBUTION": -0.25, "UTAD": -0.30,
            "MARKDOWN": -0.15,
            "UNCLEAR": 0.0,
        }
        score += phase_scores.get(row_phase, 0.0)

        # CMF
        if row_cmf.get("cmf_signal") == "BUYING":   score += 0.15
        elif row_cmf.get("cmf_signal") == "SELLING": score -= 0.15

        # OBV divergence
        div = row_cmf.get("obv_divergence", "NONE")
        if div == "BULLISH_DIV":   score += 0.15
        elif div == "BEARISH_DIV": score -= 0.15

        scores.iloc[i] = float(np.clip(score, -1, 1))

    # Smooth slightly
    return scores.rolling(3, min_periods=1).mean().rename("smart_money_score")


# ══════════════════════════════════════════════════════════════════
# MAIN PIPELINE — run everything and return a single enriched DF
# ══════════════════════════════════════════════════════════════════

def run_volume_analysis(df: pd.DataFrame) -> dict:
    """
    Run all 5 methods and return a dict:
        enriched_df     — df with all indicator columns attached
        vpin            — Series
        evr             — DataFrame
        phases          — Series
        vp              — volume profile dict
        cmf_obv         — DataFrame
        smart_score     — Series in [-1, +1]
        summary         — plain-English summary dict for the UI
    """
    vpin    = compute_vpin(df)
    evr     = compute_effort_vs_result(df)
    phases  = compute_wyckoff_phases(df)
    vp      = compute_volume_profile(df)
    cmf_obv = compute_cmf_obv(df)
    score   = compute_smart_money_score(df, vpin, evr, phases, cmf_obv)

    enriched = df.copy()
    enriched["VPIN"]          = vpin
    enriched["effort"]        = evr["effort"]
    enriched["result"]        = evr["result"]
    enriched["evr_signal"]    = evr["evr_signal"]
    enriched["wyckoff_phase"] = phases
    enriched["OBV"]           = cmf_obv["OBV"]
    enriched["CMF"]           = cmf_obv["CMF"]
    enriched["cmf_signal"]    = cmf_obv["cmf_signal"]
    enriched["obv_div"]       = cmf_obv["obv_divergence"]
    enriched["smart_score"]   = score

    # Summary of latest bar
    last         = enriched.iloc[-1]
    cur_score    = float(last["smart_score"])
    cur_phase    = str(last["wyckoff_phase"])
    cur_vpin     = float(last["VPIN"]) if not np.isnan(last["VPIN"]) else 0.0
    cur_cmf      = float(last["CMF"])  if not np.isnan(last["CMF"])  else 0.0
    cur_obv_div  = str(last["obv_div"])
    cur_evr      = str(last["evr_signal"])

    if cur_score >= SMART_SCORE_ACCUMULATE:
        verdict = "ACCUMULATION"
        verdict_detail = "Multiple signals suggest a large player is quietly buying"
    elif cur_score <= SMART_SCORE_DISTRIBUTE:
        verdict = "DISTRIBUTION"
        verdict_detail = "Multiple signals suggest a large player is quietly selling"
    else:
        verdict = "UNCLEAR"
        verdict_detail = "Signals are mixed — no clear institutional footprint"

    summary = {
        "verdict":        verdict,
        "verdict_detail": verdict_detail,
        "smart_score":    round(cur_score, 3),
        "wyckoff_phase":  cur_phase,
        "vpin":           round(cur_vpin, 3),
        "vpin_label":     "Informed flow" if cur_vpin > 0.5 else "Uninformed/retail",
        "cmf":            round(cur_cmf, 3),
        "cmf_signal":     str(last["cmf_signal"]),
        "obv_divergence": cur_obv_div,
        "evr_signal":     cur_evr,
        "poc":            vp["poc"],
        "value_area_high": vp["value_area_high"],
        "value_area_low":  vp["value_area_low"],
        "absorption_bars": int((evr["evr_signal"] != "NORMAL").sum()),
        "dominant_phase": phases.value_counts().index[0] if not phases.empty else "UNCLEAR",
    }

    return {
        "enriched_df": enriched,
        "vpin":        vpin,
        "evr":         evr,
        "phases":      phases,
        "vp":          vp,
        "cmf_obv":     cmf_obv,
        "smart_score": score,
        "summary":     summary,
    }
