"""
Quant Engine
────────────
Two independent analytical layers:

─────────────────────────────────────────────────────────────────────
1. BUY / SELL VOLUME DECOMPOSITION  (best available without order book)
─────────────────────────────────────────────────────────────────────
Yahoo Finance gives us OHLCV bars, not tick data or Level 2.
We use three complementary methods and combine them:

  a) Tick Rule (price-direction proxy)
     If Close > prev Close → all volume is buyer-initiated (BUY).
     If Close < prev Close → all volume is seller-initiated (SELL).
     If unchanged → split 50/50.
     Simple but widely used in academic microstructure research.

  b) Bulk Volume Classification (BVC) — Easley et al. 2012
     Uses the bar's standardized price change relative to a rolling σ
     to estimate the fraction of volume that is buyer-initiated.
        buy_frac = CDF( ΔP / σ )   (normal CDF)
     More nuanced than tick rule for wide bars.

  c) Candle body ratio
     A long green body (close >> open) suggests most transactions
     were at the ask (buyer aggression). A red body → seller aggression.
        buy_frac = (Close - Low) / (High - Low)   [Heikin-Ashi proxy]

  Final split = average of all three fractions × total volume.
  This gives a BUY_volume and SELL_volume for every bar.

  Derived metrics:
    • Net delta        = BUY_vol − SELL_vol
    • Cumulative delta = running sum of net delta (like OBV but signed)
    • Flow imbalance   = BUY_vol / (BUY_vol + SELL_vol)
    • Volume-weighted price pressure = Σ(signed_vol × price) / Σ(vol)

─────────────────────────────────────────────────────────────────────
2. MONTE CARLO PRICE SIMULATION  (Geometric Brownian Motion + fat tails)
─────────────────────────────────────────────────────────────────────
Uses the historical log-return distribution of the current ticker
(not a generic market assumption) to simulate N forward paths.

  S(t+1) = S(t) × exp( (μ - σ²/2)Δt + σ√Δt × Z )

  where Z is drawn from a Student-t distribution (df=5) to capture
  the fat tails characteristic of individual stock returns.
  μ and σ are estimated from the trailing bars in the window.

  Output:
    • MC_paths         — (N_SIMS × HORIZON) array of price paths
    • Percentile bands — 5th, 25th, 50th, 75th, 95th
    • Prob(up)         — fraction of paths ending above current price
    • Expected return  — mean terminal return across all paths
    • VaR 95%          — 5th percentile terminal return
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from core.config import (
    FLOW_IMBALANCE_STRONG,
    MC_CONFIDENCE_LEVELS,
    MC_HORIZON_BARS,
    MC_SIMULATIONS,
    QUANT_VOL_WINDOW,
    SELL_TAX_RATE,
    BROKER_COMMISSION,
)

_RNG = np.random.default_rng(seed=42)

# ── Buy/Sell volume decomposition ─────────────────────────────────────────────

def _tick_rule_frac(df: pd.DataFrame) -> pd.Series:
    """Fraction of volume classified as buy-initiated via Tick Rule."""
    price_chg = df["Close"].diff()
    frac = pd.Series(0.5, index=df.index)
    frac[price_chg > 0] = 1.0
    frac[price_chg < 0] = 0.0
    return frac


def _bvc_frac(df: pd.DataFrame) -> pd.Series:
    """Bulk Volume Classification fraction (Easley et al. 2012)."""
    log_ret = np.log(df["Close"] / df["Close"].shift(1))
    sigma   = log_ret.rolling(QUANT_VOL_WINDOW).std().replace(0, np.nan)
    z_score = log_ret / sigma
    # Normal CDF maps z-score → buy fraction
    return z_score.apply(lambda z: float(stats.norm.cdf(z)) if not np.isnan(z) else 0.5)


def _candle_body_frac(df: pd.DataFrame) -> pd.Series:
    """Candle body ratio: position of close within the high-low range."""
    hl_range = (df["High"] - df["Low"]).replace(0, np.nan)
    return ((df["Close"] - df["Low"]) / hl_range).fillna(0.5)


def decompose_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add buy/sell volume columns and derived flow metrics.

    New columns:
        buy_frac        — blended buy fraction [0, 1]
        buy_vol         — estimated buy volume
        sell_vol        — estimated sell volume
        net_delta       — buy_vol - sell_vol
        cum_delta       — cumulative net delta
        flow_imbalance  — buy_vol / total_vol
        pressure        — 'BUY' | 'SELL' | 'NEUTRAL'
    """
    df = df.copy()

    tick   = _tick_rule_frac(df)
    bvc    = _bvc_frac(df)
    candle = _candle_body_frac(df)

    # Equal-weight blend of three methods
    df["buy_frac"]  = (tick + bvc + candle) / 3.0
    df["buy_vol"]   = (df["buy_frac"] * df["Volume"]).round()
    df["sell_vol"]  = ((1 - df["buy_frac"]) * df["Volume"]).round()
    df["net_delta"] = df["buy_vol"] - df["sell_vol"]
    df["cum_delta"] = df["net_delta"].cumsum()

    total = (df["buy_vol"] + df["sell_vol"]).replace(0, np.nan)
    df["flow_imbalance"] = df["buy_vol"] / total

    df["pressure"] = "NEUTRAL"
    df.loc[df["flow_imbalance"] >= FLOW_IMBALANCE_STRONG, "pressure"] = "BUY"
    df.loc[df["flow_imbalance"] <= (1 - FLOW_IMBALANCE_STRONG), "pressure"] = "SELL"

    # Rolling smoothed delta (VWAP-style weighted)
    df["delta_smooth"] = df["net_delta"].rolling(QUANT_VOL_WINDOW).mean()

    # Volume-weighted price pressure score
    signed_vol = df["net_delta"] * df["Close"]
    df["vwap_pressure"] = signed_vol.rolling(QUANT_VOL_WINDOW).sum() / \
                          df["Volume"].rolling(QUANT_VOL_WINDOW).sum().replace(0, np.nan)

    return df


def flow_summary(df: pd.DataFrame) -> dict:
    """Aggregate buy/sell flow stats from the enriched DataFrame."""
    if "buy_vol" not in df.columns:
        df = decompose_volume(df)

    total_buy  = df["buy_vol"].sum()
    total_sell = df["sell_vol"].sum()
    total_vol  = total_buy + total_sell
    imbalance  = total_buy / total_vol if total_vol > 0 else 0.5

    last_n = df.tail(5)
    recent_delta = last_n["net_delta"].sum()

    return {
        "total_buy_vol":   int(total_buy),
        "total_sell_vol":  int(total_sell),
        "total_vol":       int(total_vol),
        "imbalance":       round(float(imbalance), 4),
        "recent_delta":    int(recent_delta),
        "cum_delta_final": int(df["cum_delta"].iloc[-1]),
        "pressure":        df["pressure"].iloc[-1],
        "dominant_side":   "BUY" if imbalance > 0.5 else "SELL",
    }


# ── Monte Carlo simulation ─────────────────────────────────────────────────────

def run_monte_carlo(
    df: pd.DataFrame,
    n_sims: int = MC_SIMULATIONS,
    horizon: int = MC_HORIZON_BARS,
    use_t_dist: bool = True,
) -> dict:
    """
    Simulate N forward price paths using GBM with fat-tail returns.

    Parameters
    ----------
    df          : enriched OHLCV DataFrame (must have at least 20 rows)
    n_sims      : number of simulation paths
    horizon     : bars to project forward
    use_t_dist  : if True, draw from Student-t (df=5) instead of Normal

    Returns
    -------
    dict with keys:
        paths           — (n_sims × horizon) ndarray of simulated prices
        percentiles     — dict of {pct_label: array_of_length_horizon}
        last_price      — float, the starting price
        prob_up         — float, fraction of paths ending above last_price
        expected_return — float, mean terminal log-return
        var_95          — float, 5th pct terminal log-return (Value-at-Risk)
        mu              — estimated drift per bar
        sigma           — estimated volatility per bar
        horizon         — int
        n_sims          — int
        cost_pct        — round-trip cost for reference
    """
    log_rets = np.log(df["Close"] / df["Close"].shift(1)).dropna()
    if len(log_rets) < 10:
        return {}

    mu    = float(log_rets.mean())
    sigma = float(log_rets.std())
    last  = float(df["Close"].iloc[-1])

    # Draw random shocks
    if use_t_dist:
        shocks = _RNG.standard_t(df=5, size=(n_sims, horizon))
        # Scale to match historical σ
        shocks = shocks / np.sqrt(5 / 3) * sigma
    else:
        shocks = _RNG.normal(0, sigma, size=(n_sims, horizon))

    # GBM step: log-return per bar
    drift      = mu - 0.5 * sigma ** 2
    log_paths  = drift + shocks                       # (n_sims, horizon)
    cum_paths  = np.cumsum(log_paths, axis=1)         # cumulative log-returns
    price_paths = last * np.exp(cum_paths)            # absolute prices

    terminal    = price_paths[:, -1]
    term_rets   = np.log(terminal / last)

    pct_dict = {}
    for level in MC_CONFIDENCE_LEVELS:
        pct_dict[f"p{level}"] = np.percentile(price_paths, level, axis=0)

    cost_pct = (SELL_TAX_RATE + BROKER_COMMISSION * 2) * 100

    return {
        "paths":           price_paths,
        "percentiles":     pct_dict,
        "last_price":      last,
        "prob_up":         float(np.mean(terminal > last)),
        "expected_return": float(np.mean(term_rets)) * 100,
        "var_95":          float(np.percentile(term_rets, 5)) * 100,
        "var_99":          float(np.percentile(term_rets, 1)) * 100,
        "best_case":       float(np.percentile(term_rets, 95)) * 100,
        "mu_per_bar":      mu * 100,
        "sigma_per_bar":   sigma * 100,
        "horizon":         horizon,
        "n_sims":          n_sims,
        "cost_pct":        cost_pct,
    }


def mc_signal(mc: dict) -> tuple[str, str]:
    """Derive a simple directional signal from Monte Carlo output."""
    if not mc:
        return "WAIT", "Insufficient data"
    prob_up = mc["prob_up"]
    exp_ret = mc["expected_return"]
    cost    = mc["cost_pct"]

    if prob_up >= 0.60 and exp_ret > cost:
        return "BULLISH", f"{prob_up:.0%} of paths end higher, exp. return {exp_ret:+.3f}%"
    if prob_up <= 0.40 and exp_ret < -cost:
        return "BEARISH", f"Only {prob_up:.0%} of paths end higher, exp. return {exp_ret:+.3f}%"
    return "NEUTRAL", f"Mixed paths — {prob_up:.0%} up, exp. return {exp_ret:+.3f}%"
