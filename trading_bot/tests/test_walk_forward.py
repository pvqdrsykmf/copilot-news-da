import pytest

from trading_bot.backtest import WalkForwardOptimizer
from trading_bot.strategies import MomentumStrategy


def test_walk_forward_produces_oos_metrics(synthetic_ohlcv) -> None:
    wf = WalkForwardOptimizer(
        strategy_cls=MomentumStrategy,
        param_grid={
            "lookback_days": [40, 80],
            "skip_days": [5],
            "n_top": [1, 2],
            "rebalance_days": [20],
        },
        train_days=200,
        test_days=80,
        objective="sharpe",
    )
    result = wf.run(synthetic_ohlcv)

    assert len(result.windows) >= 1
    # Le finestre di test devono essere temporalmente consecutive e
    # successive a quelle di train
    for w in result.windows:
        assert w.test_start > w.train_end
        assert "best_params" not in dir(w) or w.best_params  # non vuoto
        assert "sharpe" in w.test_metrics

    assert not result.stitched_equity.empty
    assert "sharpe" in result.oos_metrics


def test_walk_forward_anchored_vs_rolling(synthetic_ohlcv) -> None:
    common_kwargs = dict(
        strategy_cls=MomentumStrategy,
        param_grid={"lookback_days": [60], "skip_days": [5], "n_top": [1]},
        train_days=200,
        test_days=60,
    )
    anchored = WalkForwardOptimizer(**common_kwargs, anchored=True).run(synthetic_ohlcv)
    rolling = WalkForwardOptimizer(**common_kwargs, anchored=False).run(synthetic_ohlcv)
    # Anchored ha train_start sempre uguale alla prima data; rolling no
    assert all(w.train_start == anchored.windows[0].train_start for w in anchored.windows)
    if len(rolling.windows) >= 2:
        assert rolling.windows[1].train_start > rolling.windows[0].train_start


def test_walk_forward_insufficient_history(synthetic_ohlcv) -> None:
    wf = WalkForwardOptimizer(
        strategy_cls=MomentumStrategy,
        param_grid={"lookback_days": [60]},
        train_days=10_000,  # più dei dati disponibili
        test_days=100,
    )
    with pytest.raises(ValueError, match="storia insufficiente"):
        wf.run(synthetic_ohlcv)
