"""Interfaccia base per tutte le strategie.

Ogni strategia trasforma uno snapshot di dati storici in una lista di Signal.
Il signal NON specifica la size — è il risk manager che decide quanto allocare.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"  # chiudi posizione esistente


@dataclass(slots=True)
class Signal:
    """Decisione di trading per uno specifico simbolo a una data data."""

    symbol: str
    signal: SignalType
    timestamp: datetime
    confidence: float = 1.0  # in [0, 1], usato dal risk sizer
    target_weight: float | None = None  # frazione del portafoglio (opz.)
    metadata: dict[str, float] = field(default_factory=dict)  # feature usate

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")


class Strategy(ABC):
    """Strategia pluggabile.

    Convenzioni:
    - input: DataFrame MultiIndex (symbol, date) con colonne OHLCV
    - output: lista di Signal per la data di valutazione
    - parametri: esposti come attributi/keyword nel costruttore
    """

    name: str = "base"

    def __init__(self, **params: float | int | str) -> None:
        self.params = params

    @abstractmethod
    def generate_signals(
        self,
        data: pd.DataFrame,
        as_of: datetime | None = None,
    ) -> list[Signal]:
        """Genera segnali sulla base dei dati fino ad `as_of` (incluso).

        Se as_of è None usa l'ultimo timestamp disponibile.
        """

    def required_lookback(self) -> int:
        """Numero minimo di barre necessarie. Override nelle sottoclassi."""
        return 200

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.params})"
