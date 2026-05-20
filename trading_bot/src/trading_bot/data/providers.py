"""Provider di dati di mercato.

- YFinanceProvider: gratis, ideale per backtest storici.
- AlpacaDataProvider: live + recente, richiede API key.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from trading_bot.config import get_settings
from trading_bot.monitoring import get_logger

log = get_logger(__name__)


class DataProvider(Protocol):
    """Interfaccia comune di un provider di dati storici OHLCV."""

    def get_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Day",
    ) -> pd.DataFrame:
        """Ritorna DataFrame con MultiIndex (symbol, date) e colonne OHLCV."""
        ...


class YFinanceProvider:
    """Provider gratuito basato su Yahoo Finance.

    Usato per backtest storici. Non usare in live (latenza/affidabilità non
    sufficienti per esecuzione).
    """

    def get_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Day",
    ) -> pd.DataFrame:
        import yfinance as yf

        interval_map = {"1Day": "1d", "1Hour": "1h", "1Min": "1m"}
        interval = interval_map.get(timeframe, "1d")

        log.info(
            "yfinance.download",
            symbols=symbols,
            start=start.date().isoformat(),
            end=end.date().isoformat(),
            interval=interval,
        )

        raw = yf.download(
            tickers=symbols,
            start=start,
            end=end,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # Normalizza in MultiIndex (symbol, date) → OHLCV
        frames: list[pd.DataFrame] = []
        if len(symbols) == 1:
            df = raw.copy()
            df["symbol"] = symbols[0]
            df = df.reset_index().rename(columns={"Date": "date", "Datetime": "date"})
            frames.append(df)
        else:
            for sym in symbols:
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym].copy()
                df["symbol"] = sym
                df = df.reset_index().rename(columns={"Date": "date", "Datetime": "date"})
                frames.append(df)

        if not frames:
            raise RuntimeError("Nessun dato scaricato — controlla symbol e date")

        out = pd.concat(frames, ignore_index=True)
        out.columns = [c.lower() if isinstance(c, str) else c for c in out.columns]
        out = out.set_index(["symbol", "date"]).sort_index()
        return out[["open", "high", "low", "close", "volume"]]


class AlpacaDataProvider:
    """Provider Alpaca per dati recenti e live.

    Richiede API key valide. Per backtest molto lunghi preferire yfinance
    (Alpaca free tier limita la storia disponibile).
    """

    def __init__(self) -> None:
        from alpaca.data.historical import (
            CryptoHistoricalDataClient,
            StockHistoricalDataClient,
        )

        s = get_settings()
        key = s.alpaca_api_key.get_secret_value()
        secret = s.alpaca_api_secret.get_secret_value()
        if not key or not secret:
            raise RuntimeError(
                "ALPACA_API_KEY / ALPACA_API_SECRET non configurate in .env"
            )
        self._stocks = StockHistoricalDataClient(key, secret)
        self._crypto = CryptoHistoricalDataClient(key, secret)

    def get_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Day",
    ) -> pd.DataFrame:
        from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        tf_map = {
            "1Day": TimeFrame.Day,
            "1Hour": TimeFrame.Hour,
            "1Min": TimeFrame.Minute,
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        }
        tf = tf_map.get(timeframe, TimeFrame.Day)

        crypto = [s for s in symbols if "/" in s]
        stocks = [s for s in symbols if "/" not in s]
        frames: list[pd.DataFrame] = []

        if stocks:
            req = StockBarsRequest(
                symbol_or_symbols=stocks, timeframe=tf, start=start, end=end
            )
            bars = self._stocks.get_stock_bars(req).df
            frames.append(bars)
        if crypto:
            req = CryptoBarsRequest(
                symbol_or_symbols=crypto, timeframe=tf, start=start, end=end
            )
            bars = self._crypto.get_crypto_bars(req).df
            frames.append(bars)

        if not frames:
            raise RuntimeError("Nessun simbolo valido richiesto")

        df = pd.concat(frames)
        # alpaca-py usa MultiIndex (symbol, timestamp); rinomina per uniformità
        df = df.rename_axis(index={"timestamp": "date"})
        return df[["open", "high", "low", "close", "volume"]]
