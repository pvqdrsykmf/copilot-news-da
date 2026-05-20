"""Mean reversion su RSI estremi.

Logica: compra asset liquidi quando l'RSI a 2 periodi scende sotto soglia
ipervenduta (Larry Connors style), vendi quando torna sopra una soglia
di chiusura. Funziona su mega-cap US e indici, NON su micro-cap (dove
RSI estremi spesso = bad news strutturali).

Edge empirico: documentato in letteratura su S&P 500 dal 2000+.
Funziona meglio in regime non-trending. In trend forti perde, quindi va
sempre combinato con altre strategie o filtri di regime.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from trading_bot.monitoring import get_logger
from trading_bot.strategies.base import Signal, SignalType, Strategy

log = get_logger(__name__)


def rsi(series: pd.Series, period: int = 2) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"

    def __init__(
        self,
        rsi_period: int = 2,
        oversold: float = 10.0,
        exit_rsi: float = 70.0,
        trend_filter_sma: int = 200,
        max_concurrent: int = 5,
    ) -> None:
        super().__init__(
            rsi_period=rsi_period,
            oversold=oversold,
            exit_rsi=exit_rsi,
            trend_filter_sma=trend_filter_sma,
            max_concurrent=max_concurrent,
        )
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.exit_rsi = exit_rsi
        self.trend_filter_sma = trend_filter_sma
        self.max_concurrent = max_concurrent

    def required_lookback(self) -> int:
        return max(self.trend_filter_sma + 5, 50)

    def generate_signals(
        self,
        data: pd.DataFrame,
        as_of: datetime | None = None,
    ) -> list[Signal]:
        if data.empty:
            return []

        closes = data["close"].unstack(level="symbol").sort_index()
        if as_of is not None:
            closes = closes.loc[:as_of]

        if len(closes) < self.required_lookback():
            return []

        end = closes.index[-1]
        sma = closes.rolling(self.trend_filter_sma).mean().iloc[-1]
        last = closes.iloc[-1]

        rsi_df = closes.apply(lambda s: rsi(s, self.rsi_period))
        last_rsi = rsi_df.iloc[-1]

        signals: list[Signal] = []
        # BUY: prezzo > SMA200 (regime rialzista) AND RSI(2) molto basso
        buy_mask = (last > sma) & (last_rsi < self.oversold)
        sell_mask = last_rsi > self.exit_rsi

        # Ordina i candidati buy per RSI più basso (più estremo = più convinto)
        buy_candidates = last_rsi[buy_mask].sort_values().head(self.max_concurrent)

        for sym in buy_candidates.index:
            # confidence inversamente proporzionale all'RSI
            conf = float(max(0.0, min(1.0, (self.oversold - last_rsi[sym]) / self.oversold)))
            signals.append(
                Signal(
                    symbol=sym,
                    signal=SignalType.BUY,
                    timestamp=end if isinstance(end, datetime) else end.to_pydatetime(),
                    confidence=conf,
                    metadata={
                        "rsi": float(last_rsi[sym]),
                        "price": float(last[sym]),
                        "sma200": float(sma[sym]),
                    },
                )
            )

        for sym in last_rsi[sell_mask].index:
            signals.append(
                Signal(
                    symbol=sym,
                    signal=SignalType.CLOSE,
                    timestamp=end if isinstance(end, datetime) else end.to_pydatetime(),
                    metadata={"rsi": float(last_rsi[sym])},
                )
            )

        log.info(
            "mean_reversion.signals",
            n_buy=len(buy_candidates),
            n_close=int(sell_mask.sum()),
        )
        return signals
