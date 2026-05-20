"""Universi di asset selezionabili dalle strategie.

Asset liquidi, alta capitalizzazione, fee basse — quello che vuoi quando il
capitale è piccolo. Niente penny stock, niente fantasiose mid-cap illiquide.
"""

from __future__ import annotations

# ETF settoriali e indici principali — molto liquidi, ideali per momentum.
SECTOR_ETFS: list[str] = [
    "XLK",   # Tech
    "XLF",   # Finance
    "XLE",   # Energy
    "XLV",   # Health
    "XLI",   # Industrial
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLRE",  # Real Estate
    "XLC",   # Communications
]

# Mega-cap US — ottime per mean reversion (alta liquidità, news-driven).
MEGA_CAP_US: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "AVGO", "JPM", "V",
    "WMT", "UNH", "MA", "HD", "PG",
]

# Indici/ETF benchmark.
BENCHMARKS: list[str] = ["SPY", "QQQ", "IWM", "DIA"]

# Crypto disponibili su Alpaca (formato "BTC/USD").
CRYPTO_ALPACA: list[str] = [
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "AVAX/USD",
    "LINK/USD",
]

UNIVERSES: dict[str, list[str]] = {
    "sector_etfs": SECTOR_ETFS,
    "mega_cap": MEGA_CAP_US,
    "benchmarks": BENCHMARKS,
    "crypto": CRYPTO_ALPACA,
    "all_stocks": SECTOR_ETFS + MEGA_CAP_US + BENCHMARKS,
}
