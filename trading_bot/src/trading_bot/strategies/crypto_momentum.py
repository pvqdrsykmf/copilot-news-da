"""Momentum cross-sectional su crypto (timeframe corto).

Crypto è 24/7 con vol ~3x quella delle equity. Conseguenze pratiche:
- Timeframe più corto: ~1 mese di lookback invece di 6
- Rebalance più frequente (settimanale)
- Position sizing più conservativo (la max_position_pct viene già applicata
  dal sizer, ma qui usiamo n_top più alto per diversificare)

Edge: il momentum funziona anche su crypto ma con maggior noise. Va sempre
combinato con position sizing prudente — drawdown del 50%+ sono normali
nelle crypto anche con strategie sane.
"""

from __future__ import annotations

from trading_bot.strategies.momentum import MomentumStrategy


class CryptoMomentumStrategy(MomentumStrategy):
    """Variante di MomentumStrategy con default tarati su crypto."""

    name = "crypto_momentum"

    def __init__(
        self,
        lookback_days: int = 30,
        skip_days: int = 3,
        n_top: int = 3,
        rebalance_days: int = 7,
        min_momentum: float = 0.0,
    ) -> None:
        super().__init__(
            lookback_days=lookback_days,
            skip_days=skip_days,
            n_top=n_top,
            rebalance_days=rebalance_days,
            min_momentum=min_momentum,
        )
