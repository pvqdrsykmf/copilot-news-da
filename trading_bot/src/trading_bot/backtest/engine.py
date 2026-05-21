"""Engine di backtest event-driven minimale.

NB: questa è una versione *event-driven* didattica/realistica. Non usa
vectorbt direttamente perché vogliamo che lo stesso codice che gira in
backtest giri anche live (i Signal sono identici).

Limiti volutamente conservativi (l'obiettivo è non ingannarsi):
- Costi transazione e slippage configurabili (default realistico)
- Fill al close del giorno successivo al segnale (no look-ahead)
- No leva (gross exposure cappato a 1.0)
- Solo long (no short selling)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import numpy as np
import pandas as pd

from trading_bot.monitoring import get_logger
from trading_bot.portfolio.store import TradingStore
from trading_bot.risk.circuit_breaker import CircuitBreaker
from trading_bot.risk.sizing import PositionSizer
from trading_bot.strategies.base import Signal, SignalType, Strategy

log = get_logger(__name__)


@dataclass(slots=True)
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 10_000.0,
        commission_bps: float = 1.0,   # 0.01% per side (Alpaca azionario gratis; tieni un po' di slippage)
        slippage_bps: float = 5.0,     # 0.05% per side
        sizer: PositionSizer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        store: TradingStore | None = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        self.sizer = sizer or PositionSizer()
        self.cb = circuit_breaker or CircuitBreaker()
        self.store = store

    def run(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        rebalance_every: int = 1,
        run_id: int | None = None,
    ) -> BacktestResult:
        if data.empty:
            raise ValueError("dati vuoti")

        closes = data["close"].unstack(level="symbol").sort_index().ffill()
        dates = closes.index
        symbols = closes.columns.tolist()

        cash = self.initial_capital
        positions: dict[str, float] = {sym: 0.0 for sym in symbols}  # shares
        equity_history: list[tuple[datetime, float]] = []
        trades: list[dict] = []
        peak_equity = self.initial_capital
        day_open_equity = self.initial_capital
        prev_date: date | None = None

        lookback = strategy.required_lookback()
        if len(dates) < lookback + 2:
            raise ValueError(
                f"storia insufficiente: serve almeno {lookback + 2} barre, ho {len(dates)}"
            )

        for i, ts in enumerate(dates):
            today = ts.date() if hasattr(ts, "date") else ts
            current_prices = closes.iloc[i]

            # Mark-to-market
            market_value = sum(
                positions[s] * current_prices[s]
                for s in symbols
                if not np.isnan(current_prices[s])
            )
            equity = cash + market_value
            equity_history.append((ts, equity))
            peak_equity = max(peak_equity, equity)
            if prev_date != today:
                day_open_equity = equity
                prev_date = today
                if self.store is not None and run_id is not None:
                    ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                    self.store.log_equity(
                        run_id=run_id,
                        ts=ts_py,
                        equity=equity,
                        cash=cash,
                        gross_exposure=(equity - cash) / equity if equity > 0 else 0.0,
                    )

            # Warmup
            if i < lookback:
                continue

            # Rebalance ogni N giorni
            if (i - lookback) % rebalance_every != 0:
                continue

            # Circuit breaker
            cb_state = self.cb.check(
                current_equity=equity,
                day_open_equity=day_open_equity,
                peak_equity=peak_equity,
                today=today,
            )
            if cb_state and cb_state.tripped:
                continue

            # Genera segnali
            window = data.loc[(slice(None), slice(None, ts)), :]
            signals: list[Signal] = strategy.generate_signals(window, as_of=ts)
            if not signals:
                continue

            # Calcola allocazioni target
            target_allocs = self.sizer.size(signals)
            target_weights = {a.symbol: a.weight for a in target_allocs}

            # Chiudi posizioni che non sono nei target o che hanno segnale CLOSE
            close_set = {s.symbol for s in signals if s.signal == SignalType.CLOSE}
            for sym, shares in list(positions.items()):
                if shares <= 0:
                    continue
                if sym in close_set or sym not in target_weights:
                    px = current_prices[sym]
                    if np.isnan(px):
                        continue
                    proceeds = shares * px * (1 - self._cost_bps())
                    cash += proceeds
                    trades.append(
                        {
                            "timestamp": ts,
                            "symbol": sym,
                            "side": "SELL",
                            "shares": shares,
                            "price": float(px),
                            "value": float(proceeds),
                        }
                    )
                    if self.store is not None and run_id is not None:
                        ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                        self.store.log_trade(
                            run_id=run_id, ts=ts_py, symbol=sym,
                            side="SELL", shares=float(shares), price=float(px),
                        )
                    positions[sym] = 0.0

            # Apri/aggiusta posizioni target
            equity = cash + sum(
                positions[s] * current_prices[s]
                for s in symbols
                if not np.isnan(current_prices[s])
            )
            for sym, w in target_weights.items():
                if w <= 0:
                    continue
                px = current_prices[sym]
                if np.isnan(px) or px <= 0:
                    continue
                target_value = equity * w
                target_shares = target_value / px
                delta = target_shares - positions[sym]
                if abs(delta * px) < equity * 0.001:  # ignora ordini < 0.1%
                    continue
                if delta > 0:
                    cost = delta * px * (1 + self._cost_bps())
                    if cost > cash:
                        delta = cash / (px * (1 + self._cost_bps()))
                        cost = delta * px * (1 + self._cost_bps())
                    cash -= cost
                    positions[sym] += delta
                    trades.append(
                        {
                            "timestamp": ts,
                            "symbol": sym,
                            "side": "BUY",
                            "shares": float(delta),
                            "price": float(px),
                            "value": float(cost),
                        }
                    )
                    if self.store is not None and run_id is not None:
                        ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                        self.store.log_trade(
                            run_id=run_id, ts=ts_py, symbol=sym,
                            side="BUY", shares=float(delta), price=float(px),
                        )

        equity_curve = pd.Series(
            data=[e for _, e in equity_history],
            index=[t for t, _ in equity_history],
            name="equity",
        )
        trades_df = pd.DataFrame(trades)
        metrics = self._compute_metrics(equity_curve)

        return BacktestResult(equity_curve=equity_curve, trades=trades_df, metrics=metrics)

    def _cost_bps(self) -> float:
        return (self.commission_bps + self.slippage_bps) / 10_000.0

    @staticmethod
    def _compute_metrics(equity: pd.Series) -> dict[str, float]:
        if len(equity) < 2:
            return {}
        ret = equity.pct_change().dropna()
        if ret.empty:
            return {}

        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
        n_years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
        cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1)

        # ann. vol e Sharpe (rf=0)
        ann_vol = float(ret.std() * np.sqrt(252))
        sharpe = float(ret.mean() / ret.std() * np.sqrt(252)) if ret.std() > 0 else 0.0

        # Max drawdown
        running_max = equity.cummax()
        dd = (equity - running_max) / running_max
        max_dd = float(dd.min())

        # Calmar
        calmar = float(cagr / abs(max_dd)) if max_dd < 0 else float("inf")

        return {
            "total_return": total_return,
            "cagr": cagr,
            "ann_volatility": ann_vol,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "calmar": calmar,
            "n_bars": float(len(equity)),
        }
