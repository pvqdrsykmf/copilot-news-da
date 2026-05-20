from datetime import date

import pytest

from trading_bot.risk import CircuitBreaker, PositionSizer
from trading_bot.strategies.base import Signal, SignalType


def _sig(sym: str, conf: float = 1.0, weight: float | None = None) -> Signal:
    from datetime import datetime

    return Signal(
        symbol=sym,
        signal=SignalType.BUY,
        timestamp=datetime(2024, 1, 1),
        confidence=conf,
        target_weight=weight,
    )


def test_sizer_caps_position_at_max_pct() -> None:
    sizer = PositionSizer(max_position_pct=0.10, mode="equal_weight")
    allocs = sizer.size([_sig("A"), _sig("B")])
    assert all(a.weight <= 0.10 for a in allocs)


def test_sizer_confidence_weighted_sums_to_gross() -> None:
    sizer = PositionSizer(max_position_pct=1.0, max_gross_exposure=1.0,
                          mode="confidence_weighted")
    allocs = sizer.size([_sig("A", conf=1.0), _sig("B", conf=0.5)])
    total = sum(a.weight for a in allocs)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_sizer_respects_strategy_target_weight() -> None:
    sizer = PositionSizer(max_position_pct=0.10)
    allocs = sizer.size([_sig("A", weight=0.5), _sig("B", weight=0.5)])
    assert all(a.weight == 0.10 for a in allocs)


def test_circuit_breaker_daily_loss() -> None:
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, max_drawdown_pct=0.20)
    s = cb.check(
        current_equity=9_600,
        day_open_equity=10_000,
        peak_equity=10_000,
        today=date(2024, 1, 2),
    )
    assert s is not None and s.tripped


def test_circuit_breaker_hard_drawdown_persists() -> None:
    cb = CircuitBreaker(daily_loss_limit_pct=0.10, max_drawdown_pct=0.15)
    s1 = cb.check(8_400, 9_900, 10_000, date(2024, 1, 2))
    assert s1 is not None and s1.tripped
    # Anche un giorno dopo deve essere ancora tripped
    s2 = cb.check(8_500, 8_400, 10_000, date(2024, 1, 3))
    assert s2 is not None and s2.tripped


def test_circuit_breaker_clean_state() -> None:
    cb = CircuitBreaker()
    s = cb.check(10_100, 10_000, 10_100, date(2024, 1, 2))
    assert s is None
