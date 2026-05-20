"""Position sizing — quanto allocare a un segnale.

Filosofia: il sizer è il guardrail. Limita la dimensione massima per
posizione e l'esposizione lorda totale, indipendentemente da quanto
"convinta" sia la strategia.

Modalità:
- equal_weight: peso uguale tra tutti i segnali aperti
- confidence_weighted: peso proporzionale alla confidence del segnale
- fractional_kelly: Kelly frazionato basato su edge stimato (richiede stats)
"""

from __future__ import annotations

from dataclasses import dataclass

from trading_bot.monitoring import get_logger
from trading_bot.strategies.base import Signal, SignalType

log = get_logger(__name__)


@dataclass(slots=True)
class TargetAllocation:
    symbol: str
    weight: float  # frazione del portafoglio totale, in [0, max_position_pct]
    rationale: str


class PositionSizer:
    """Calcola le allocazioni target a partire da segnali e vincoli."""

    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_gross_exposure: float = 1.0,
        mode: str = "confidence_weighted",
    ) -> None:
        if not 0 < max_position_pct <= 1:
            raise ValueError("max_position_pct must be in (0, 1]")
        if max_gross_exposure <= 0:
            raise ValueError("max_gross_exposure must be > 0")
        if mode not in {"equal_weight", "confidence_weighted"}:
            raise ValueError(f"unknown sizing mode: {mode}")
        self.max_position_pct = max_position_pct
        self.max_gross_exposure = max_gross_exposure
        self.mode = mode

    def size(self, signals: list[Signal]) -> list[TargetAllocation]:
        buys = [s for s in signals if s.signal == SignalType.BUY]
        if not buys:
            return []

        # Se la strategia ha già un target_weight esplicito, lo rispettiamo
        # (sempre cappato dai limiti globali).
        if all(s.target_weight is not None for s in buys):
            allocs = [
                TargetAllocation(
                    symbol=s.symbol,
                    weight=min(s.target_weight or 0.0, self.max_position_pct),
                    rationale="strategy_target",
                )
                for s in buys
            ]
        elif self.mode == "equal_weight":
            w = min(self.max_position_pct, self.max_gross_exposure / len(buys))
            allocs = [
                TargetAllocation(symbol=s.symbol, weight=w, rationale="equal_weight")
                for s in buys
            ]
        else:  # confidence_weighted
            total_conf = sum(s.confidence for s in buys) or 1.0
            raw = [
                (s.symbol, (s.confidence / total_conf) * self.max_gross_exposure)
                for s in buys
            ]
            allocs = [
                TargetAllocation(
                    symbol=sym,
                    weight=min(w, self.max_position_pct),
                    rationale="confidence_weighted",
                )
                for sym, w in raw
            ]

        # Hard cap su esposizione lorda totale
        total = sum(a.weight for a in allocs)
        if total > self.max_gross_exposure:
            factor = self.max_gross_exposure / total
            for a in allocs:
                a.weight *= factor
            log.warning(
                "sizing.gross_exposure_capped",
                requested=total,
                limit=self.max_gross_exposure,
                factor=factor,
            )

        return allocs
