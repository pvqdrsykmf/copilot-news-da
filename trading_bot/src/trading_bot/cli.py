"""CLI principale del trading bot."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from trading_bot import __version__
from trading_bot.backtest import BacktestEngine
from trading_bot.config import get_settings
from trading_bot.data import UNIVERSES, YFinanceProvider
from trading_bot.monitoring import get_logger, setup_logging
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
    )
    result = engine.run(strat, data, rebalance_every=rebalance)

    _print_metrics(result.metrics, result.equity_curve, result.trades)

    if out:
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        result.equity_curve.to_csv(out_path / "equity_curve.csv")
        result.trades.to_csv(out_path / "trades.csv", index=False)
        console.print(f"\n[green]Report salvato in {out_path}[/green]")


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
