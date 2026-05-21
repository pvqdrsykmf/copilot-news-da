"""CLI principale del trading bot."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from trading_bot import __version__
from trading_bot.backtest import BacktestEngine, WalkForwardOptimizer
from trading_bot.config import get_settings
from trading_bot.data import UNIVERSES, YFinanceProvider
from trading_bot.monitoring import get_logger, setup_logging
from trading_bot.portfolio import TradingStore
from trading_bot.risk import CircuitBreaker, PositionSizer
from trading_bot.strategies import STRATEGY_REGISTRY

console = Console()
log = get_logger(__name__)


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """Trading bot quantitativo su Alpaca."""
    s = get_settings()
    setup_logging(level=s.log_level, log_dir=s.log_dir)


@cli.command()
@click.option("--strategy", "-s", required=True, type=click.Choice(list(STRATEGY_REGISTRY)))
@click.option("--universe", "-u", default="sector_etfs", type=click.Choice(list(UNIVERSES)))
@click.option("--start", default="2018-01-01", help="data inizio YYYY-MM-DD")
@click.option("--end", default=None, help="data fine YYYY-MM-DD (default: oggi)")
@click.option("--capital", default=10_000.0, type=float, help="capitale iniziale")
@click.option("--rebalance", default=5, type=int, help="ogni quanti bar rebalance")
@click.option("--out", default=None, type=click.Path(), help="cartella output report")
def backtest(
    strategy: str,
    universe: str,
    start: str,
    end: str | None,
    capital: float,
    rebalance: int,
    out: str | None,
) -> None:
    """Esegue un backtest storico con dati yfinance."""
    s = get_settings()
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end) if end else datetime.now()

    symbols = UNIVERSES[universe]
    console.print(f"[bold]Backtest[/bold] strategy={strategy} universe={universe}")
    console.print(f"  periodo: {start_dt.date()} → {end_dt.date()}")
    console.print(f"  capitale: ${capital:,.0f}  rebalance: ogni {rebalance} bar")
    console.print(f"  symbols ({len(symbols)}): {', '.join(symbols)}")

    provider = YFinanceProvider()
    data = provider.get_bars(symbols, start_dt, end_dt, "1Day")

    strat_cls = STRATEGY_REGISTRY[strategy]
    strat = strat_cls()

    store = TradingStore(s.db_path)
    run_id = store.start_run(
        kind="backtest",
        strategy=strategy,
        universe=universe,
        params=strat.params,
        initial_capital=capital,
    )

    engine = BacktestEngine(
        initial_capital=capital,
        sizer=PositionSizer(
            max_position_pct=s.max_position_pct,
            max_gross_exposure=s.max_gross_exposure,
        ),
        circuit_breaker=CircuitBreaker(
            daily_loss_limit_pct=s.daily_loss_limit_pct,
            max_drawdown_pct=s.max_drawdown_pct,
        ),
        store=store,
    )
    result = engine.run(strat, data, rebalance_every=rebalance, run_id=run_id)

    _print_metrics(result.metrics, result.equity_curve, result.trades)
    console.print(f"\n[dim]run_id={run_id} salvato in {s.db_path}[/dim]")

    if out:
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        result.equity_curve.to_csv(out_path / "equity_curve.csv")
        result.trades.to_csv(out_path / "trades.csv", index=False)
        console.print(f"[green]Report salvato in {out_path}[/green]")


@cli.command()
def status() -> None:
    """Stato account Alpaca (paper o live)."""
    from trading_bot.execution import AlpacaBroker

    broker = AlpacaBroker()
    acc = broker.account()
    positions = broker.positions()

    mode = "PAPER" if acc.paper else "[red bold]LIVE[/red bold]"
    console.print(f"\n[bold]Account Alpaca[/bold] ({mode})")
    console.print(f"  Equity:        ${acc.equity:,.2f}")
    console.print(f"  Cash:          ${acc.cash:,.2f}")
    console.print(f"  Buying power:  ${acc.buying_power:,.2f}")
    console.print(f"  Day trades:    {acc.daytrade_count}")

    if positions:
        t = Table(title="Posizioni")
        for col in ("Symbol", "Qty", "Avg entry", "Market value", "Unrealized P/L"):
            t.add_column(col, justify="right")
        for p in positions:
            color = "green" if p.unrealized_pl >= 0 else "red"
            t.add_row(
                p.symbol,
                f"{p.qty:.4f}",
                f"${p.avg_entry_price:.2f}",
                f"${p.market_value:.2f}",
                f"[{color}]${p.unrealized_pl:+.2f}[/{color}]",
            )
        console.print(t)
    else:
        console.print("[dim]Nessuna posizione aperta.[/dim]")


@cli.command()
@click.option("--strategy", "-s", required=True, type=click.Choice(list(STRATEGY_REGISTRY)))
@click.option("--universe", "-u", default="sector_etfs", type=click.Choice(list(UNIVERSES)))
@click.option("--dry-run", is_flag=True, help="genera segnali ma non invia ordini")
def paper(strategy: str, universe: str, dry_run: bool) -> None:
    """Genera segnali con dati attuali e (opzionalmente) invia ordini in paper."""
    from trading_bot.execution import AlpacaBroker

    s = get_settings()
    if not s.alpaca_paper and not dry_run:
        raise click.ClickException(
            "Sei in modalità LIVE. Usa --dry-run o cambia ALPACA_LIVE=false in .env"
        )

    symbols = UNIVERSES[universe]
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=400)

    console.print(f"Recupero dati per {len(symbols)} simboli…")
    provider = YFinanceProvider()
    data = provider.get_bars(symbols, start_dt, end_dt, "1Day")

    strat = STRATEGY_REGISTRY[strategy]()
    signals = strat.generate_signals(data)

    sizer = PositionSizer(
        max_position_pct=s.max_position_pct,
        max_gross_exposure=s.max_gross_exposure,
    )
    allocs = sizer.size(signals)

    t = Table(title=f"Segnali strategia {strategy}")
    for col in ("Symbol", "Signal", "Confidence", "Target weight"):
        t.add_column(col, justify="right")
    for sig in signals:
        weight = next((a.weight for a in allocs if a.symbol == sig.symbol), 0.0)
        t.add_row(
            sig.symbol,
            sig.signal.value,
            f"{sig.confidence:.2f}",
            f"{weight:.2%}" if weight else "—",
        )
    console.print(t)

    if dry_run:
        console.print("[yellow]--dry-run: nessun ordine inviato[/yellow]")
        return

    broker = AlpacaBroker()
    acc = broker.account()
    for a in allocs:
        notional = round(acc.equity * a.weight, 2)
        if notional < 1:
            continue
        broker.submit_market_order(symbol=a.symbol, notional=notional, side="buy")
    console.print("[green]Ordini inviati al paper account.[/green]")


@cli.command()
@click.option("--strategy", "-s", required=True, type=click.Choice(list(STRATEGY_REGISTRY)))
@click.option("--universe", "-u", default="sector_etfs", type=click.Choice(list(UNIVERSES)))
@click.option("--start", default="2018-01-01")
@click.option("--end", default=None)
@click.option("--train-days", default=504, type=int, help="lunghezza train window (giorni)")
@click.option("--test-days", default=126, type=int, help="lunghezza test window (giorni)")
@click.option("--objective", default="sharpe", type=click.Choice(["sharpe", "calmar", "cagr"]))
@click.option("--anchored/--rolling", default=False)
@click.option("--out", default=None, type=click.Path())
def walkforward(
    strategy: str,
    universe: str,
    start: str,
    end: str | None,
    train_days: int,
    test_days: int,
    objective: str,
    anchored: bool,
    out: str | None,
) -> None:
    """Walk-forward optimization su grid di parametri (out-of-sample only)."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end) if end else datetime.now()
    symbols = UNIVERSES[universe]
    console.print(
        f"[bold]Walk-forward[/bold] strategy={strategy} universe={universe}\n"
        f"  periodo: {start_dt.date()} → {end_dt.date()}\n"
        f"  train/test: {train_days}/{test_days} bar, "
        f"{'anchored' if anchored else 'rolling'}"
    )

    provider = YFinanceProvider()
    data = provider.get_bars(symbols, start_dt, end_dt, "1Day")

    # Grid sensibili per default; nelle prossime iterazioni si parametrizza
    grids = {
        "momentum": {
            "lookback_days": [63, 126, 189],
            "skip_days": [5, 21],
            "n_top": [2, 3, 4],
            "rebalance_days": [21],
        },
        "crypto_momentum": {
            "lookback_days": [14, 30, 60],
            "skip_days": [3],
            "n_top": [2, 3],
            "rebalance_days": [7],
        },
        "mean_reversion": {
            "rsi_period": [2, 3],
            "oversold": [5, 10, 15],
            "exit_rsi": [60, 70, 80],
            "trend_filter_sma": [150, 200],
        },
    }
    if strategy not in grids:
        raise click.ClickException(f"nessun grid definito per {strategy}")

    wf = WalkForwardOptimizer(
        strategy_cls=STRATEGY_REGISTRY[strategy],
        param_grid=grids[strategy],
        train_days=train_days,
        test_days=test_days,
        objective=objective,
        anchored=anchored,
    )
    result = wf.run(data)

    summary = result.summary_df()
    console.print("\n[bold]Finestre walk-forward (out-of-sample)[/bold]")
    console.print(summary.to_string(index=False))

    console.print("\n[bold]Metriche aggregate out-of-sample[/bold]")
    t = Table()
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    fmt = {
        "total_return": "{:.2%}", "cagr": "{:.2%}", "ann_volatility": "{:.2%}",
        "sharpe": "{:.2f}", "max_drawdown": "{:.2%}", "calmar": "{:.2f}",
        "n_bars": "{:.0f}",
    }
    for k, v in result.oos_metrics.items():
        t.add_row(k, fmt.get(k, "{}").format(v))
    console.print(t)

    if out:
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        result.stitched_equity.to_csv(out_path / "wf_oos_equity.csv")
        summary.to_csv(out_path / "wf_windows.csv", index=False)
        console.print(f"\n[green]Output salvato in {out_path}[/green]")


@cli.command()
@click.option("--last", default=30, type=int, help="trade degli ultimi N giorni")
@click.option("--run", "run_id", default=None, type=int, help="dettaglio di un run specifico")
def report(last: int, run_id: int | None) -> None:
    """Mostra runs e trade salvati in SQLite."""
    s = get_settings()
    store = TradingStore(s.db_path)

    if run_id is not None:
        trades = store.trades_for_run(run_id)
        equity = store.equity_curve(run_id)
        console.print(f"[bold]Run #{run_id}[/bold] — {len(trades)} trade")
        if not equity.empty:
            console.print(
                f"Equity: ${equity.iloc[0]:,.2f} → ${equity.iloc[-1]:,.2f} "
                f"({(equity.iloc[-1]/equity.iloc[0]-1):+.2%})"
            )
        if trades:
            t = Table(title="Trade")
            for col in ("ts", "symbol", "side", "shares", "price", "value"):
                t.add_column(col, justify="right")
            for tr in trades[-20:]:
                t.add_row(
                    tr["ts"][:19], tr["symbol"], tr["side"],
                    f"{tr['shares']:.4f}", f"${tr['price']:.2f}", f"${tr['value']:.2f}",
                )
            console.print(t)
        return

    runs = store.list_runs(limit=20)
    if runs:
        t = Table(title="Run recenti")
        for col in ("id", "kind", "strategy", "universe", "started_at", "capital"):
            t.add_column(col)
        for r in runs:
            t.add_row(
                str(r["id"]), r["kind"], r["strategy"],
                r["universe"] or "—", r["started_at"][:19],
                f"${(r['initial_capital'] or 0):,.0f}",
            )
        console.print(t)

    recent = store.recent_trades(last)
    console.print(f"\n[bold]Trade ultimi {last} giorni[/bold]: {len(recent)}")
    if recent:
        t = Table()
        for col in ("ts", "run", "symbol", "side", "shares", "price"):
            t.add_column(col, justify="right")
        for tr in recent[:30]:
            t.add_row(
                tr["ts"][:19], str(tr["run_id"]), tr["symbol"], tr["side"],
                f"{tr['shares']:.4f}", f"${tr['price']:.2f}",
            )
        console.print(t)


def _print_metrics(metrics: dict, equity, trades) -> None:
    t = Table(title="Metriche backtest")
    t.add_column("Metric")
    t.add_column("Value", justify="right")
    fmt = {
        "total_return": "{:.2%}",
        "cagr": "{:.2%}",
        "ann_volatility": "{:.2%}",
        "sharpe": "{:.2f}",
        "max_drawdown": "{:.2%}",
        "calmar": "{:.2f}",
        "n_bars": "{:.0f}",
    }
    for k, v in metrics.items():
        t.add_row(k, fmt.get(k, "{}").format(v))
    console.print(t)
    console.print(f"\nTrade totali: {len(trades)}")
    if not equity.empty:
        console.print(
            f"Equity finale: ${equity.iloc[-1]:,.2f} "
            f"(da ${equity.iloc[0]:,.2f})"
        )


if __name__ == "__main__":
    cli()
