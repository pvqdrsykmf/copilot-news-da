"""Persistenza in SQLite di run, trade, snapshot equity e segnali.

Tutto loggato qui è leggibile a posteriori per debug, audit e reportistica.
Schema volutamente piatto e auto-migrabile: ogni installazione crea le tabelle
al primo uso, niente ORM, solo sqlite3 + JSON per i metadata.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_bot.monitoring import get_logger

log = get_logger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    kind            TEXT NOT NULL,           -- 'backtest' | 'paper' | 'live'
    strategy        TEXT NOT NULL,
    universe        TEXT,
    params          TEXT,                    -- JSON
    initial_capital REAL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    ts          TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,               -- 'BUY' | 'SELL'
    shares      REAL NOT NULL,
    price       REAL NOT NULL,
    value       REAL NOT NULL,
    order_id    TEXT,
    meta        TEXT                          -- JSON con feature/decisione
);
CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id);
CREATE INDEX IF NOT EXISTS idx_trades_ts  ON trades(ts);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    INTEGER NOT NULL REFERENCES runs(id),
    ts        TEXT NOT NULL,
    equity    REAL NOT NULL,
    cash      REAL,
    gross_exposure REAL
);
CREATE INDEX IF NOT EXISTS idx_eq_run ON equity_snapshots(run_id);

CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    ts          TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    confidence  REAL,
    target_weight REAL,
    meta        TEXT                          -- JSON con feature usate
);
CREATE INDEX IF NOT EXISTS idx_signals_run ON signals(run_id);
"""


@dataclass(slots=True)
class RunRecord:
    id: int
    started_at: datetime
    kind: str
    strategy: str


class TradingStore:
    """Wrapper sottile su sqlite3 per persistenza locale.

    Connessione thread-locale: ogni metodo apre/chiude la propria connection.
    Per workload normali (bot retail, qualche ordine al giorno) è più che ok.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ---- runs ----
    def start_run(
        self,
        kind: str,
        strategy: str,
        universe: str | None = None,
        params: dict[str, Any] | None = None,
        initial_capital: float | None = None,
        notes: str | None = None,
    ) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO runs(started_at, kind, strategy, universe, params, "
                "initial_capital, notes) VALUES (?,?,?,?,?,?,?)",
                (
                    datetime.utcnow().isoformat(),
                    kind,
                    strategy,
                    universe,
                    json.dumps(params or {}, default=str),
                    initial_capital,
                    notes,
                ),
            )
            run_id = cur.lastrowid
            log.info("store.run.started", run_id=run_id, kind=kind, strategy=strategy)
            return int(run_id)

    def list_runs(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- trades ----
    def log_trade(
        self,
        run_id: int,
        ts: datetime,
        symbol: str,
        side: str,
        shares: float,
        price: float,
        order_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO trades(run_id, ts, symbol, side, shares, price, value, "
                "order_id, meta) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    ts.isoformat(),
                    symbol,
                    side.upper(),
                    float(shares),
                    float(price),
                    float(shares * price),
                    order_id,
                    json.dumps(meta or {}, default=str),
                ),
            )

    def trades_for_run(self, run_id: int) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM trades WHERE run_id=? ORDER BY ts", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def recent_trades(self, days: int = 30) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM trades WHERE ts >= datetime('now', ?) ORDER BY ts DESC",
                (f"-{days} days",),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- equity ----
    def log_equity(
        self,
        run_id: int,
        ts: datetime,
        equity: float,
        cash: float | None = None,
        gross_exposure: float | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO equity_snapshots(run_id, ts, equity, cash, gross_exposure) "
                "VALUES (?,?,?,?,?)",
                (run_id, ts.isoformat(), float(equity), cash, gross_exposure),
            )

    def equity_curve(self, run_id: int):
        import pandas as pd

        with self._conn() as c:
            df = pd.read_sql_query(
                "SELECT ts, equity FROM equity_snapshots WHERE run_id=? ORDER BY ts",
                c,
                params=(run_id,),
                parse_dates=["ts"],
            )
        if df.empty:
            return pd.Series(dtype=float, name="equity")
        return df.set_index("ts")["equity"]

    # ---- signals ----
    def log_signal(
        self,
        run_id: int,
        ts: datetime,
        symbol: str,
        signal_type: str,
        confidence: float | None = None,
        target_weight: float | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO signals(run_id, ts, symbol, signal_type, confidence, "
                "target_weight, meta) VALUES (?,?,?,?,?,?,?)",
                (
                    run_id,
                    ts.isoformat(),
                    symbol,
                    signal_type,
                    confidence,
                    target_weight,
                    json.dumps(meta or {}, default=str),
                ),
            )
