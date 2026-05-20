# Trading Bot — Esperimento quantitativo

Bot autonomo per investimenti in borsa con approccio quantitativo professionale.
Broker: **Alpaca** (paper + live). Stack: **Python 3.11+**.

> ⚠️ **Disclaimer.** Questo software è un esperimento personale. Non è
> consulenza finanziaria. Il trading algoritmico comporta rischio di perdita
> totale del capitale. Non operare mai con denaro che non puoi permetterti
> di perdere. Validare sempre in paper trading per mesi prima del live.

## Obiettivo

Target finale: **€500/mese netti** entro 12–18 mesi, raggiunto scalando
capitale solo se le metriche reali del paper/live confermano l'edge.

Vedi [`docs/ROADMAP.md`](docs/ROADMAP.md) per le fasi.

## Quick start

```bash
cd trading_bot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# inserisci ALPACA_API_KEY e ALPACA_API_SECRET (paper)

# Esempi
trading-bot backtest --strategy momentum --start 2020-01-01 --end 2024-12-31
trading-bot paper    --strategy momentum
trading-bot report   --last 30
```

## Struttura

```
src/trading_bot/
  config.py         # settings da env
  data/             # provider dati (yfinance, alpaca)
  strategies/       # strategie pluggabili (momentum, mean reversion, ...)
  backtest/         # engine di backtest + walk-forward
  risk/             # position sizing, stop loss, circuit breaker
  execution/        # client broker (Alpaca) + order manager
  portfolio/        # tracker posizioni e P&L
  monitoring/       # logging strutturato, report giornalieri
  cli.py            # CLI principale
```

## Filosofia

1. **Paper first.** Nessuna esecuzione live finché walk-forward e paper di
   almeno 60 giorni non danno Sharpe > 1.0 e max drawdown < 15%.
2. **Risk before return.** Position sizing e stop-loss sono hard-coded; un
   bug nello strategy module non può azzerare il conto.
3. **No overfitting.** Walk-forward obbligatorio. Niente parametri scelti
   guardando i dati out-of-sample.
4. **Auditabile.** Ogni decisione e ordine viene loggato in modo strutturato
   con tutti i feature al momento della decisione.

## Stato attuale

- [x] Struttura progetto + tooling
- [x] Config + segreti via env
- [x] Provider dati (yfinance gratis, Alpaca live)
- [x] Strategy base + 2 strategie (momentum, mean reversion)
- [x] Engine di backtest minimale
- [x] Risk management (sizing, stop loss, circuit breaker)
- [x] Client broker Alpaca (paper)
- [x] CLI con comandi backtest/paper/report
- [ ] Walk-forward optimization
- [ ] Dashboard di monitoring
- [ ] Persistenza trade in SQLite
- [ ] Strategie ML (fase 2)
- [ ] Live trading abilitato (fase 3, manuale)

Vedi `docs/ROADMAP.md` per dettagli sulla prossima fase.
