# Architettura

```
┌──────────────────────────────────────────────────────────────┐
│                          CLI                                 │
│  backtest │ paper │ status │ report                          │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   DATA       │ →  │  STRATEGIES  │ →  │     RISK     │
│  providers   │    │   (signals)  │    │   (sizing)   │
└──────────────┘    └──────────────┘    └──────────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                  │  BACKTEST    │    │  EXECUTION   │    │   MONITOR    │
                  │   engine     │    │   (Alpaca)   │    │ logs/reports │
                  └──────────────┘    └──────────────┘    └──────────────┘
```

## Principi

1. **Stesso codice paper/live/backtest.** Le strategie producono `Signal`,
   indipendenti dal motore che li consuma. Il backtest e il live differiscono
   solo nel consumatore (BacktestEngine vs AlpacaBroker).

2. **Sicurezza by default.** Per fare live trading servono DUE flag espliciti
   (`ALPACA_LIVE=true` + `LIVE_CONFIRM=I_KNOW_WHAT_I_AM_DOING`). Default = paper.

3. **Risk management come gate.** Il PositionSizer NON è un suggerimento,
   è un cap hard. Il CircuitBreaker può bloccare totalmente l'esecuzione
   anche con un bug di strategia.

4. **Auditabilità.** Ogni segnale e ordine viene loggato con timestamp,
   feature usate, motivazione. Necessario sia per debug che per migliorare
   le strategie.

## Flusso di un trade in paper/live

```
1. CLI invoca `paper -s momentum`
2. DataProvider scarica gli ultimi N giorni di OHLCV
3. Strategy.generate_signals(data) → [Signal(BUY/CLOSE), ...]
4. PositionSizer.size(signals) → [TargetAllocation(weight=…), ...]
5. CircuitBreaker.check(equity, drawdown) → ok/tripped
6. Se ok: AlpacaBroker.submit_market_order(notional=equity*weight)
7. Monitor logga decisione + ordine + risposta broker
```

## Aggiungere una nuova strategia

1. Crea `src/trading_bot/strategies/my_strat.py` ereditando da `Strategy`
2. Implementa `generate_signals(data, as_of)` ritornando `list[Signal]`
3. Registrala in `strategies/__init__.py::STRATEGY_REGISTRY`
4. Aggiungi test in `tests/test_strategies.py` usando la fixture
   `synthetic_ohlcv`
5. Backtest su dati storici reali prima di considerarla pronta per paper

## Aggiungere un nuovo broker

1. Crea una classe parallela ad `AlpacaBroker` con la stessa interfaccia
   (`account()`, `positions()`, `submit_market_order()`, `close_position()`)
2. La CLI consuma l'astrazione → switch trasparente

## Cosa NON è ancora implementato

- Persistenza in DB (trade history attualmente solo in memoria/log)
- Walk-forward optimization (sì backtest, no rolling window automatico)
- Order management avanzato (limit, OCO, trailing stop)
- WebSocket streaming dei prezzi (al momento polling/pull)
- Multi-strategy allocator (al momento una strategia per processo)
