"""Walk-forward optimization.

Filosofia: il vero test di una strategia non è il backtest in-sample, è
quanto regge fuori campione. Walk-forward simula la situazione reale:
ad ogni finestra ottimizzi i parametri sui dati passati ("train") e poi
li applichi sul periodo successivo ("test"), senza rivederli.

Le metriche aggregate sul concatenato dei periodi di test rappresentano
una stima onesta di come la strategia avrebbe performato se fosse stata
gestita realisticamente nel tempo.

Schema (anchored rolling):

    [============ train1 ============][== test1 ==]
    [================== train2 =================][== test2 ==]
    [======================== train3 =====================][== test3 ==]

Oppure (rolling fixed-size):

    [== train1 ==][== test1 ==]
       [== train2 ==][== test2 ==]
          [== train3 ==][== test3 ==]
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.backtest.engine import BacktestEngine
from trading_bot.monitoring import get_logger
from trading_bot.strategies.base import Strategy

log = get_logger(__name__)


@dataclass(slots=True)
class WalkForwardWindow:
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    best_params: dict[str, Any]
    train_metric: float
    test_metrics: dict[str, float]
    test_equity_curve: pd.Series


@dataclass(slots=True)
class WalkForwardResult:
    windows: list[WalkForwardWindow]
    stitched_equity: pd.Series
    oos_metrics: dict[str, float]
    param_grid_used: dict[str, list[Any]] = field(default_factory=dict)

    def summary_df(self) -> pd.DataFrame:
        rows = []
        for w in self.windows:
            row = {
                "train_start": w.train_start.date(),
                "train_end": w.train_end.date(),
                "test_start": w.test_start.date(),
                "test_end": w.test_end.date(),
                "train_metric": round(w.train_metric, 4),
                **{f"test_{k}": round(v, 4) for k, v in w.test_metrics.items()},
                **{f"p_{k}": v for k, v in w.best_params.items()},
            }
            rows.append(row)
        return pd.DataFrame(rows)


class WalkForwardOptimizer:
    """Esegue walk-forward su una strategia con un grid di parametri.

    - Suddivide il periodo totale in N finestre (train, test) consecutive
    - Per ogni finestra: cerca i parametri migliori in-sample, poi valuta out-of-sample
    - Concatena le equity curve out-of-sample
    """

    def __init__(
        self,
        strategy_cls: type[Strategy],
        param_grid: dict[str, Iterable[Any]],
        train_days: int = 504,           # ~2 anni di trading days
        test_days: int = 126,            # ~6 mesi
        step_days: int | None = None,    # default = test_days (no overlap dei test)
        objective: str = "sharpe",       # metrica da massimizzare in-sample
        anchored: bool = False,          # se True, train_start fisso (training cumula)
        rebalance_every: int = 5,
        initial_capital: float = 10_000.0,
    ) -> None:
        if objective not in {"sharpe", "calmar", "cagr"}:
            raise ValueError(f"objective non supportato: {objective}")
        self.strategy_cls = strategy_cls
        self.param_grid = {k: list(v) for k, v in param_grid.items()}
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days or test_days
        self.objective = objective
        self.anchored = anchored
        self.rebalance_every = rebalance_every
        self.initial_capital = initial_capital

    def _iter_param_combos(self) -> list[dict[str, Any]]:
        keys = list(self.param_grid)
        combos = list(product(*[self.param_grid[k] for k in keys]))
        return [dict(zip(keys, c, strict=True)) for c in combos]

    def run(self, data: pd.DataFrame) -> WalkForwardResult:
        if data.empty:
            raise ValueError("dati vuoti")

        # Costruisci indice univoco delle date di trading
        dates = data.index.get_level_values("date").unique().sort_values()
        n = len(dates)
        min_required = self.train_days + self.test_days
        if n < min_required:
            raise ValueError(
                f"storia insufficiente: serve almeno {min_required} bar, ho {n}"
            )

        windows: list[WalkForwardWindow] = []
        combos = self._iter_param_combos()
        log.info(
            "walkforward.start",
            n_combos=len(combos),
            train_days=self.train_days,
            test_days=self.test_days,
        )

        start_idx = 0
        while True:
            train_lo = 0 if self.anchored else start_idx
            train_hi = start_idx + self.train_days
            test_lo = train_hi
            test_hi = test_lo + self.test_days
            if test_hi > n:
                break

            train_dates = dates[train_lo:train_hi]
            test_dates = dates[test_lo:test_hi]
            train_slice = data.loc[(slice(None), train_dates), :]
            full_slice = data.loc[(slice(None), dates[train_lo:test_hi]), :]

            best = self._optimize_one_window(train_slice, combos)
            log.info(
                "walkforward.window.optimized",
                train=f"{train_dates[0].date()}→{train_dates[-1].date()}",
                test=f"{test_dates[0].date()}→{test_dates[-1].date()}",
                best=best["params"],
                train_metric=round(best["metric"], 4),
            )

            # Valuta out-of-sample lanciando il backtest sull'intera finestra
            # (train+test) e ritagliando l'equity sulla parte test.
            strat = self.strategy_cls(**best["params"])
            engine = BacktestEngine(initial_capital=self.initial_capital)
            result = engine.run(strat, full_slice, rebalance_every=self.rebalance_every)
            full_equity = result.equity_curve
            test_equity = full_equity.loc[full_equity.index >= test_dates[0]]
            test_equity = test_equity / test_equity.iloc[0] * self.initial_capital
            test_metrics = BacktestEngine._compute_metrics(test_equity)

            windows.append(
                WalkForwardWindow(
                    train_start=train_dates[0].to_pydatetime(),
                    train_end=train_dates[-1].to_pydatetime(),
                    test_start=test_dates[0].to_pydatetime(),
                    test_end=test_dates[-1].to_pydatetime(),
                    best_params=best["params"],
                    train_metric=best["metric"],
                    test_metrics=test_metrics,
                    test_equity_curve=test_equity,
                )
            )

            start_idx += self.step_days

        # Concatena equity out-of-sample reinvestendo
        stitched = self._stitch_equity([w.test_equity_curve for w in windows])
        oos_metrics = BacktestEngine._compute_metrics(stitched)

        return WalkForwardResult(
            windows=windows,
            stitched_equity=stitched,
            oos_metrics=oos_metrics,
            param_grid_used=self.param_grid,
        )

    def _optimize_one_window(
        self, train_data: pd.DataFrame, combos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        best_metric = -np.inf
        best_params: dict[str, Any] = {}
        for params in combos:
            try:
                strat = self.strategy_cls(**params)
                engine = BacktestEngine(initial_capital=self.initial_capital)
                res = engine.run(strat, train_data, rebalance_every=self.rebalance_every)
                m = res.metrics.get(self.objective)
                if m is None or np.isnan(m) or np.isinf(m):
                    continue
                if m > best_metric:
                    best_metric = m
                    best_params = params
            except (ValueError, RuntimeError) as e:
                log.debug("walkforward.combo.failed", params=params, error=str(e))
                continue
        if not best_params:
            # Fallback: prendi la prima combo se nessuna ha prodotto metriche
            best_params = combos[0]
            best_metric = 0.0
        return {"params": best_params, "metric": best_metric}

    @staticmethod
    def _stitch_equity(curves: list[pd.Series]) -> pd.Series:
        """Concatena equity out-of-sample reinvestendo i rendimenti.

        Ogni curva parte da initial_capital; ricostruiamo il ritorno cumulato
        come prodotto dei (equity_finale/equity_iniziale) di ogni finestra.
        """
        if not curves:
            return pd.Series(dtype=float)
        pieces: list[pd.Series] = []
        cumulative = 1.0
        for c in curves:
            if c.empty:
                continue
            normalized = c / c.iloc[0]
            scaled = normalized * cumulative
            cumulative = float(scaled.iloc[-1])
            pieces.append(scaled)
        if not pieces:
            return pd.Series(dtype=float)
        stitched = pd.concat(pieces)
        stitched = stitched[~stitched.index.duplicated(keep="last")]
        # Ri-scala su un capitale iniziale di riferimento (10k) per leggibilità
        return stitched * 10_000.0
