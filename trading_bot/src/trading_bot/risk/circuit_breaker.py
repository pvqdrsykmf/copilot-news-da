"""Circuit breaker — interrompe il trading quando le condizioni si deteriorano.

Due livelli di protezione:
1. Daily loss limit: se in un giorno si perde più di X%, stop fino al giorno dopo
2. Max drawdown: se DD dal picco supera Y%, stop totale (richiede intervento manuale)

Il circuit breaker è hard. Anche se la strategia "vuole" comprare, se il
breaker è aperto non si trada. Questo evita catastrofi da bug.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

from trading_bot.monitoring import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class CircuitBreakerState:
    tripped: bool
    reason: str
    triggered_at: str  # ISO date string


class CircuitBreaker:
    def __init__(
        self,
        daily_loss_limit_pct: float = 0.03,
        max_drawdown_pct: float = 0.15,
    ) -> None:
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self._daily_stop_date: date | None = None
        self._hard_stop: CircuitBreakerState | None = None

    def check(
        self,
        current_equity: float,
        day_open_equity: float,
        peak_equity: float,
        today: date,
    ) -> CircuitBreakerState | None:
        """Ritorna lo stato se è tripped, altrimenti None."""
        if self._hard_stop is not None:
            return self._hard_stop

        # Daily reset
        if self._daily_stop_date is not None and self._daily_stop_date < today:
            log.info("circuit_breaker.daily_reset", date=today.isoformat())
            self._daily_stop_date = None

        # Hard drawdown
        if peak_equity > 0:
            dd = (current_equity - peak_equity) / peak_equity
            if dd <= -self.max_drawdown_pct:
                self._hard_stop = CircuitBreakerState(
                    tripped=True,
                    reason=f"max_drawdown_breach dd={dd:.2%} limit={-self.max_drawdown_pct:.2%}",
                    triggered_at=today.isoformat(),
                )
                log.error("circuit_breaker.hard_stop", **asdict(self._hard_stop))
                return self._hard_stop

        # Daily loss
        if day_open_equity > 0:
            daily = (current_equity - day_open_equity) / day_open_equity
            if daily <= -self.daily_loss_limit_pct:
                self._daily_stop_date = today
                state = CircuitBreakerState(
                    tripped=True,
                    reason=(
                        f"daily_loss_breach daily={daily:.2%} "
                        f"limit={-self.daily_loss_limit_pct:.2%}"
                    ),
                    triggered_at=today.isoformat(),
                )
                log.warning("circuit_breaker.daily_stop", **asdict(state))
                return state

        if self._daily_stop_date == today:
            return CircuitBreakerState(
                tripped=True,
                reason="daily_stop_in_effect",
                triggered_at=today.isoformat(),
            )

        return None

    def reset_hard_stop(self, confirmation: str) -> None:
        """Reset manuale dell'hard stop. Richiede conferma esplicita."""
        if confirmation != "I_REVIEWED_THE_LOSS":
            raise RuntimeError("hard stop reset requires explicit confirmation")
        log.warning("circuit_breaker.hard_stop_reset_manual")
        self._hard_stop = None
