"""Momentum cross-sectional.

Logica: ogni N giorni, classifica gli asset dell'universo per total return
sui passati `lookback_days` (escludendo il mese più recente per evitare
short-term reversal — è una pratica standard letteratura, Jegadeesh & Titman 1993).
Prendi i top `n_top` con peso uguale, vendi tutti gli altri.

Edge empirico: documentato da decenni su equity. Funziona meglio quando
applicato a ETF settoriali liquidi (meno noise di singole azioni).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from trading_bot.monitoring import get_logger
from trading_bot.strategies.base import Signal, SignalType, Strategy

log = get_logger(__name__)


class MomentumStrategy(Strategy):
    name = "momentum"

    def __init__(
        self,
        lookback_days: int = 126,   # ~6 mesi
        skip_days: int = 21,         # salta ~1 mese (short-term reversal)
        n_top: int = 3,
        rebalance_days: int = 21,    # rebalance mensile
        min_momentum: float = 0.0,   # filtro: solo se momentum > 0 (no shorts)
    ) -> None:
        super().__init__(
            lookback_days=lookback_days,
            skip_days=skip_days,
            n_top=n_top,
            rebalance_days=rebalance_days,
            min_momentum=min_momentum,
        )
        self.lookback_days = lookback_days
        self.skip_days = skip_days
        self.n_top = n_top
        self.rebalance_days = rebalance_days
        self.min_momentum = min_momentum

    def required_lookback(self) -> int:
        return self.lookback_days + self.skip_days + 5

    def generate_signals(
        self,
        data: pd.DataFrame,
        as_of: datetime | None = None,
    ) -> list[Signal]:
        if data.empty:
            return []

        # Pivot in matrix (date x symbol) sui close
        closes = data["close"].unstack(level="symbol")
        closes = closes.sort_index()

        if as_of is not None:
            closes = closes.loc[:as_of]

        if len(closes) < self.required_lookback():
            log.warning(
                "momentum.insufficient_history",
                have=len(closes),
                need=self.required_lookback(),
            )
            return []

        end = closes.index[-1]
        # Prezzo "passato" = lookback + skip giorni fa.
        # Prezzo "recente" = skip giorni fa (escludiamo l'ultimo mese).
        try:
            ref_recent = closes.iloc[-self.skip_days - 1]
            ref_old = closes.iloc[-self.skip_days - self.lookback_days - 1]
        except IndexError:
            return []

        mom = (ref_recent / ref_old) - 1.0
        mom = mom.dropna()

        if mom.empty:
            return []

        # Filtra solo quelli sopra il minimo
        eligible = mom[mom > self.min_momentum].sort_values(ascending=False)
        winners = eligible.head(self.n_top).index.tolist()

        signals: list[Signal] = []
        target_weight = (1.0 / self.n_top) if winners else 0.0
        all_syms = mom.index.tolist()

        for sym in all_syms:
            if sym in winners:
                signals.append(
                    Signal(
                        symbol=sym,
                        signal=SignalType.BUY,
                        timestamp=end if isinstance(end, datetime) else end.to_pydatetime(),
                        confidence=min(1.0, max(0.0, float(mom[sym]))),
                        target_weight=target_weight,
                        metadata={"momentum": float(mom[sym])},
                    )
                )
            else:
                signals.append(
                    Signal(
                        symbol=sym,
                        signal=SignalType.CLOSE,
                        timestamp=end if isinstance(end, datetime) else end.to_pydatetime(),
                        confidence=0.0,
                        target_weight=0.0,
                        metadata={"momentum": float(mom[sym])},
                    )
                )

        log.info(
            "momentum.signals",
            winners=winners,
            n_eligible=len(eligible),
            top_momentum={k: round(float(v), 4) for k, v in eligible.head(5).items()},
        )
        return signals
