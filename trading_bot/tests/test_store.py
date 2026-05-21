from datetime import datetime

from trading_bot.portfolio import TradingStore


def test_store_creates_schema_on_init(tmp_path) -> None:
    store = TradingStore(tmp_path / "test.db")
    runs = store.list_runs()
    assert runs == []


def test_store_run_trade_equity_signal_lifecycle(tmp_path) -> None:
    store = TradingStore(tmp_path / "test.db")
    run_id = store.start_run(
        kind="backtest",
        strategy="momentum",
        universe="sector_etfs",
        params={"lookback_days": 126},
        initial_capital=10_000,
    )
    assert run_id > 0

    ts = datetime(2024, 6, 1, 10, 0)
    store.log_trade(run_id, ts, "XLK", "BUY", 10.0, 200.0, meta={"momentum": 0.15})
    store.log_trade(run_id, ts, "XLE", "BUY", 5.0, 80.0)
    store.log_equity(run_id, ts, equity=10_500, cash=4_500)
    store.log_signal(run_id, ts, "XLK", "BUY", confidence=0.8, target_weight=0.33)

    trades = store.trades_for_run(run_id)
    assert len(trades) == 2
    assert trades[0]["symbol"] == "XLK"
    assert trades[0]["value"] == 10.0 * 200.0

    equity = store.equity_curve(run_id)
    assert len(equity) == 1
    assert float(equity.iloc[0]) == 10_500


def test_store_recent_trades_filter(tmp_path) -> None:
    store = TradingStore(tmp_path / "test.db")
    run_id = store.start_run(kind="paper", strategy="momentum")
    # Una trade "vecchia" 60 giorni fa
    import datetime as dt
    old_ts = dt.datetime.utcnow() - dt.timedelta(days=60)
    new_ts = dt.datetime.utcnow()
    store.log_trade(run_id, old_ts, "OLD", "BUY", 1, 100)
    store.log_trade(run_id, new_ts, "NEW", "BUY", 1, 100)

    recent = store.recent_trades(days=30)
    syms = {t["symbol"] for t in recent}
    assert "NEW" in syms and "OLD" not in syms
