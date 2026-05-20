"""Fixture comuni: dati sintetici per testare strategie e backtest senza rete."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """3 simboli, 500 giorni, trend e volatilità diversi."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-01", periods=500, freq="B")
    frames: list[pd.DataFrame] = []

    specs = [
        ("TREND", 0.0008, 0.012),    # forte uptrend
        ("FLAT", 0.00005, 0.010),    # quasi flat
        ("CYCLE", 0.0003, 0.018),    # trend medio + vol alta
    ]
    for sym, mu, sigma in specs:
        rets = rng.normal(mu, sigma, len(dates))
        close = 100 * np.exp(np.cumsum(rets))
        high = close * (1 + np.abs(rng.normal(0, 0.003, len(dates))))
        low = close * (1 - np.abs(rng.normal(0, 0.003, len(dates))))
        open_ = close * (1 + rng.normal(0, 0.002, len(dates)))
        vol = rng.integers(1_000_000, 5_000_000, len(dates))
        df = pd.DataFrame(
            {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": vol,
                "symbol": sym,
                "date": dates,
            }
        )
        frames.append(df)

    out = pd.concat(frames, ignore_index=True).set_index(["symbol", "date"]).sort_index()
    return out
