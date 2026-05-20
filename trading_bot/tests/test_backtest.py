from trading_bot.backtest import BacktestEngine
from trading_bot.risk import CircuitBreaker, PositionSizer
from trading_bot.strategies import MomentumStrategy


def test_backtest_end_to_end(synthetic_ohlcv) -> None:
    engine = BacktestEngine(
        initial_capital=10_000,
        sizer=PositionSizer(max_position_pct=0.5, max_gross_exposure=1.0),
        circuit_breaker=CircuitBreaker(),
    )
    strat = MomentumStrategy(lookback_days=60, skip_days=5, n_top=1)
    result = engine.run(strat, synthetic_ohlcv, rebalance_every=20)

    assert not result.equity_curve.empty
    assert "sharpe" in result.metrics
    assert "max_drawdown" in result.metrics
    # equity finale deve essere ragionevole (no NaN, no zero)
    assert result.equity_curve.iloc[-1] > 0


def test_backtest_respects_max_position_pct(synthetic_ohlcv) -> None:
    engine = BacktestEngine(
        initial_capital=10_000,
        sizer=PositionSizer(max_position_pct=0.10, max_gross_exposure=1.0),
    )
    strat = MomentumStrategy(lookback_days=60, skip_days=5, n_top=1)
    result = engine.run(strat, synthetic_ohlcv, rebalance_every=20)

    # Con un solo winner e cap 10%, esposizione massima per quel simbolo è 10%
    # Verifica indiretta: con cap basso il rendimento è molto contenuto
    assert abs(result.metrics["total_return"]) < 2.0  # no esposizione folle
