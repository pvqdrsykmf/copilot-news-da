from trading_bot.strategies import MeanReversionStrategy, MomentumStrategy
from trading_bot.strategies.base import SignalType


def test_momentum_picks_trending_asset(synthetic_ohlcv) -> None:
    strat = MomentumStrategy(lookback_days=60, skip_days=5, n_top=1)
    signals = strat.generate_signals(synthetic_ohlcv)
    buys = [s for s in signals if s.signal == SignalType.BUY]
    assert len(buys) == 1
    # TREND ha drift positivo molto più forte
    assert buys[0].symbol == "TREND"


def test_momentum_returns_close_for_non_winners(synthetic_ohlcv) -> None:
    strat = MomentumStrategy(lookback_days=60, skip_days=5, n_top=1)
    signals = strat.generate_signals(synthetic_ohlcv)
    closes = [s for s in signals if s.signal == SignalType.CLOSE]
    assert len(closes) == 2  # gli altri due


def test_mean_reversion_runs_without_error(synthetic_ohlcv) -> None:
    strat = MeanReversionStrategy(trend_filter_sma=50)
    signals = strat.generate_signals(synthetic_ohlcv)
    # Non possiamo prevedere esattamente quanti, ma il tipo deve essere giusto
    assert all(s.signal in {SignalType.BUY, SignalType.CLOSE} for s in signals)


def test_momentum_handles_insufficient_history() -> None:
    import pandas as pd

    empty = pd.DataFrame(
        {"open": [], "high": [], "low": [], "close": [], "volume": []},
        index=pd.MultiIndex.from_tuples([], names=["symbol", "date"]),
    )
    strat = MomentumStrategy()
    assert strat.generate_signals(empty) == []
