"""
Configuration: IDX tickers, intervals, and indicator defaults.
"""
 
IDX_WATCHLIST: dict[str, str] = {
    "BBCA.JK": "Bank Central Asia",
    "BBRI.JK": "Bank Rakyat Indonesia",
    "TLKM.JK": "Telkom Indonesia",
    "ASII.JK": "Astra International",
    "BMRI.JK": "Bank Mandiri",
    "GOTO.JK": "GoTo Group",
    "UNVR.JK": "Unilever Indonesia",
    "INDF.JK": "Indofood Sukses Makmur",
    "KLBF.JK": "Kalbe Farma",
    "SMGR.JK": "Semen Indonesia",
    "FORE.JK": "Fore Coffee ",
    "HRTA.JK": "Hartadinata Abadi",
    "MINA.JK": "Sanurhasta Mitra ",
}
 
DATA_INTERVALS: list[str] = ["1m", "5m", "15m", "30m", "1h", "1d"]
DATA_PERIODS: list[str] = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
 
REFRESH_SECONDS: int = 60  # auto-refresh interval
 
IDX_OPEN_HOUR: int = 9
IDX_CLOSE_HOUR: int = 15
IDX_TIMEZONE: str = "Asia/Jakarta"
 
SELL_TAX_RATE: float = 0.001     # 0.1% final tax on sell
BROKER_COMMISSION: float = 0.0015  # typical ~0.15%
LOT_SIZE: int = 100
 
MA_SHORT: int = 20
MA_LONG: int = 50
RSI_PERIOD: int = 14
BB_PERIOD: int = 20
BB_STD: float = 2.0
 
# ── Scalping ──────────────────────────────────────────────────────────────────
SCALP_INTERVALS: list[str] = ["1m", "2m", "5m"]
SCALP_PERIODS: list[str]   = ["1d", "5d"]
 
SCALP_EMA_FAST: int   = 5      # Fast EMA for micro-trend
SCALP_EMA_SLOW: int   = 13     # Slow EMA
SCALP_RSI_PERIOD: int = 7      # Shorter RSI for scalping
SCALP_RSI_BUY: float  = 35.0   # Oversold threshold
SCALP_RSI_SELL: float = 65.0   # Overbought threshold
 
SCALP_VWAP_PERIOD: int      = 14   # VWAP rolling window
SCALP_STOCH_K: int          = 5    # Stochastic %K
SCALP_STOCH_D: int          = 3    # Stochastic %D
SCALP_ATR_PERIOD: int       = 7    # ATR for volatility-based TP/SL
 
SCALP_TARGET_PCT: float     = 0.003   # Default take-profit: 0.3%
SCALP_STOP_PCT: float       = 0.002   # Default stop-loss:   0.2%
SCALP_MIN_SIGNAL_SCORE: int = 3       # Min indicators agreeing before entry

# ── Quant dashboard ───────────────────────────────────────────────────────────
QUANT_INTERVALS: list[str]  = ["1m", "2m", "5m"]
QUANT_PERIODS: list[str]    = ["1d", "5d"]

# Buy/sell volume inference (Tick Rule)
QUANT_VOL_WINDOW: int       = 20    # rolling window for smoothing

# Monte Carlo
MC_SIMULATIONS: int         = 500   # number of forward price paths
MC_HORIZON_BARS: int        = 30    # bars ahead to project
MC_CONFIDENCE_LEVELS: list  = [5, 25, 50, 75, 95]   # percentile bands

# Volume flow imbalance threshold
FLOW_IMBALANCE_STRONG: float = 0.65   # >65% of volume on one side = strong pressure