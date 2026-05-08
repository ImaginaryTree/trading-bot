# IDX Trading Bot Dashboard

Real-time Indonesian stock dashboard built with Streamlit + yfinance.

## Project structure

```
idx_bot/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── core/
│   ├── config.py           # Constants (tickers, intervals, tax rates)
│   ├── data.py             # yfinance data fetching
│   ├── indicators.py       # Technical indicator math
│   └── signals.py          # Signal generation & aggregation
├── ui/
│   ├── charts.py           # Plotly figure builders
│   ├── watchlist.py        # Watchlist tab renderer
│   └── analysis.py         # Analysis tab renderer
└── utils/
    └── formatting.py       # Pure formatting helpers
```

## Quick start

```bash
pip install -r requirements.txt
cd idx_bot
streamlit run app.py
```

## Features

- **Watchlist tab**: live % change bar chart + sortable table for 10 IDX stocks
- **Analysis tab**: candlestick + Bollinger Bands + SMA + Volume + RSI + MACD
- **Signals**: MA crossover, RSI, Bollinger, MACD — aggregated into BUY/SELL/HOLD
- **Auto-refresh**: configurable interval (30–300s)
- **Market clock**: WIB session status in sidebar

## Disclaimer

This tool is for educational purposes only and does not constitute financial advice.
