"""Wrapper Alpaca per esecuzione ordini.

Sicurezza: di default opera in modalità *paper*. Per passare al live servono
ENTRAMBI: ALPACA_LIVE=true E LIVE_CONFIRM=I_KNOW_WHAT_I_AM_DOING.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading_bot.config import get_settings
from trading_bot.monitoring import get_logger

log = get_logger(__name__)


@dataclass(slots=True)
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    unrealized_pl: float


@dataclass(slots=True)
class AccountSnapshot:
    equity: float
    cash: float
    buying_power: float
    daytrade_count: int
    paper: bool


class AlpacaBroker:
    def __init__(self) -> None:
        from alpaca.trading.client import TradingClient

        s = get_settings()
        key = s.alpaca_api_key.get_secret_value()
        secret = s.alpaca_api_secret.get_secret_value()
        if not key or not secret:
            raise RuntimeError("ALPACA_API_KEY / ALPACA_API_SECRET non configurate")

        self._paper = s.alpaca_paper
        self._client = TradingClient(key, secret, paper=self._paper)
        log.info(
            "alpaca.broker.init",
            mode="paper" if self._paper else "LIVE",
            warning=None if self._paper else "TRADING WITH REAL MONEY",
        )

    @property
    def paper(self) -> bool:
        return self._paper

    def account(self) -> AccountSnapshot:
        a = self._client.get_account()
        return AccountSnapshot(
            equity=float(a.equity or 0),
            cash=float(a.cash or 0),
            buying_power=float(a.buying_power or 0),
            daytrade_count=int(a.daytrade_count or 0),
            paper=self._paper,
        )

    def positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.symbol,
                qty=float(p.qty or 0),
                avg_entry_price=float(p.avg_entry_price or 0),
                market_value=float(p.market_value or 0),
                unrealized_pl=float(p.unrealized_pl or 0),
            )
            for p in self._client.get_all_positions()
        ]

    def submit_market_order(
        self,
        symbol: str,
        notional: float | None = None,
        qty: float | None = None,
        side: str = "buy",
    ) -> str:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        if notional is None and qty is None:
            raise ValueError("specificare notional o qty")
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        req = MarketOrderRequest(
            symbol=symbol,
            notional=notional,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
        order = self._client.submit_order(req)
        log.info(
            "alpaca.order.submitted",
            id=str(order.id),
            symbol=symbol,
            side=side,
            notional=notional,
            qty=qty,
        )
        return str(order.id)

    def close_position(self, symbol: str) -> None:
        self._client.close_position(symbol)
        log.info("alpaca.position.closed", symbol=symbol)
