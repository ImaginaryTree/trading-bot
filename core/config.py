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

# ── Price inefficiency / opportunity hunter ───────────────────────────────────
HUNT_INTERVALS: list[str] = ["1m", "2m", "5m", "15m"]
HUNT_PERIODS: list[str]   = ["1d", "5d"]

# VWAP deviation: how far below VWAP before we call it a BUY opportunity
HUNT_VWAP_BUY_THRESH: float  = -0.003   # -0.3% below VWAP → underpriced
HUNT_VWAP_SELL_THRESH: float =  0.003   # +0.3% above VWAP → overpriced

# Mean reversion: z-score window and entry threshold
HUNT_ZSCORE_WINDOW: int   = 20          # rolling window for mean/std
HUNT_ZSCORE_BUY: float    = -2.0        # price 2 std below mean → cheap
HUNT_ZSCORE_SELL: float   =  2.0        # price 2 std above mean → expensive

# Volume surge confirms the move is real, not just noise
HUNT_VOLUME_SURGE: float  = 1.5         # 1.5× rolling average volume

# Minimum net edge required after ALL costs to flag an opportunity
HUNT_MIN_EDGE_PCT: float  = 0.001       # 0.1% net edge floor

# ATR period for dynamic TP/SL sizing
HUNT_ATR_PERIOD: int      = 7

# Backtester: bars to look ahead to check if TP or SL was hit first
HUNT_LOOKAHEAD_BARS: int  = 10

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

# ── Volume analysis / smart money detection ───────────────────────────────────
VOL_ANALYSIS_INTERVALS: list[str] = ["5m", "15m", "30m", "1h", "1d"]
VOL_ANALYSIS_PERIODS: list[str]   = ["1d", "5d", "1mo", "3mo"]

# VPIN
VPIN_BUCKET_SIZE_FACTOR: float = 0.5   # fraction of avg daily vol per bucket
VPIN_WINDOW: int               = 50    # rolling window of buckets

# Effort vs Result
EVR_WINDOW: int      = 20   # bars to compute rolling avg for anomaly detection
EVR_THRESHOLD: float = 2.0  # std devs above avg volume with below-avg range

# Volume Profile
VP_BINS: int = 30   # number of price buckets for volume profile

# Wyckoff
WYCKOFF_WINDOW: int          = 50   # bars to look back for phase detection
WYCKOFF_RANGE_THRESHOLD: float = 0.03  # max range % to consider "trading range"

# Chaikin Money Flow
CMF_WINDOW: int = 20

# Smart money score thresholds
SMART_SCORE_ACCUMULATE: float = 0.6   # score >= this → likely accumulation
SMART_SCORE_DISTRIBUTE: float = -0.6  # score <= this → likely distribution

# ── Swing trade ───────────────────────────────────────────────────────────────
SWING_INTERVALS: list[str]  = ["1h", "4h", "1d", "1wk"]
SWING_PERIODS: list[str]    = ["1mo", "3mo", "6mo", "1y"]

# Ichimoku
ICHI_TENKAN: int    = 9
ICHI_KIJUN: int     = 26
ICHI_SENKOU_B: int  = 52
ICHI_DISPLACEMENT: int = 26

# Fibonacci retracement levels
FIB_LEVELS: list[float] = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

# Supertrend
ST_ATR_PERIOD: int    = 10
ST_MULTIPLIER: float  = 3.0

# Elder Triple Screen
ELDER_WEEKLY_EMA: int = 13   # screen 1: trend on higher TF
ELDER_DAILY_STOCH: int = 14  # screen 2: oscillator
ELDER_STOCH_D: int    = 3

# Swing signal confluence: min strategies agreeing for high-confidence signal
SWING_MIN_CONFLUENCE: int = 3