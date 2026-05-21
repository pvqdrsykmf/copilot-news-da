from trading_bot.strategies.base import Signal, SignalType, Strategy
from trading_bot.strategies.crypto_momentum import CryptoMomentumStrategy
from trading_bot.strategies.mean_reversion import MeanReversionStrategy
from trading_bot.strategies.momentum import MomentumStrategy

__all__ = [
    "Signal",
    "SignalType",
    "Strategy",
    "MomentumStrategy",
    "MeanReversionStrategy",
    "CryptoMomentumStrategy",
    "STRATEGY_REGISTRY",
]


STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "crypto_momentum": CryptoMomentumStrategy,
}
