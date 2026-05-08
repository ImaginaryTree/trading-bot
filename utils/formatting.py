"""
Utilities: pure formatting helpers used by the UI layer.
"""

from __future__ import annotations


def format_idr(value: float) -> str:
    """Format a number as Indonesian Rupiah."""
    if value >= 1_000_000_000_000:
        return f"Rp {value / 1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.2f}M"
    if value >= 1_000_000:
        return f"Rp {value / 1_000_000:.2f}Jt"
    return f"Rp {value:,.0f}"


def format_change(value: float, is_pct: bool = False) -> str:
    """Return a signed string with arrow indicator."""
    suffix = "%" if is_pct else ""
    arrow = "▲" if value >= 0 else "▼"
    return f"{arrow} {abs(value):.2f}{suffix}"


def signal_color(signal: str) -> str:
    """Map signal string to a CSS/Streamlit color name."""
    return {"BUY": "green", "SELL": "red", "HOLD": "orange"}.get(signal, "gray")


def signal_emoji(signal: str) -> str:
    return {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal, "⚪")


def market_status(hour_wib: int) -> tuple[str, str]:
    """Return (status_label, color) based on WIB hour."""
    if 9 <= hour_wib < 12:
        return "🟢 Pre-noon session", "green"
    if 12 <= hour_wib < 13:
        return "🟡 Midday break", "orange"
    if 13 <= hour_wib < 15:
        return "🟢 Afternoon session", "green"
    if hour_wib == 15:
        return "🔴 Market closed (ATC)", "red"
    return "🔴 Market closed", "red"
