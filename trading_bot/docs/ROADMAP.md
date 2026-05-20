# Roadmap operativa

Approccio: **prove of edge → small live → scale**. Niente live finché non
abbiamo numeri (paper + backtest fuori campione) che dimostrano un edge reale.

## Fase 1 — Foundation (0–4 settimane)  ← *siamo qui*

Obiettivo: avere uno scheletro pulito su cui costruire.

- [x] Struttura progetto Python + tooling
- [x] Provider dati yfinance + Alpaca
- [x] Engine di backtest event-driven minimale
- [x] 2 strategie baseline (momentum cross-sectional, mean reversion RSI)
- [x] Risk management hard-coded (sizing, stop, circuit breaker)
- [x] CLI con `backtest`, `paper`, `status`
- [ ] Setup Alpaca paper account + key in `.env`
- [ ] Primo backtest reale su ETF settoriali 2018–oggi

**Done quando**: il comando `trading-bot backtest -s momentum` gira senza
errori e produce equity curve + metriche su dati storici reali.

## Fase 2 — Validation (4–12 settimane)

Obiettivo: capire se le strategie hanno edge vero o stiamo solo sovraadattando.

- [ ] Walk-forward optimization (split train/test rolling)
- [ ] Confronto vs benchmark (SPY buy-and-hold) — la strategia deve battere
      l'indice **a parità di rischio**, non solo in rendimento
- [ ] Stress test: 2018 Q4, COVID Mar 2020, 2022 bear market
- [ ] Paper trading live su Alpaca per **almeno 60 giorni**
- [ ] Confronto paper-vs-backtest: gli slippage reali devono essere ≤ stimati
- [ ] Aggiungere 1–2 strategie con edge diverso (crypto momentum, pairs trading)
- [ ] Persistenza trade/equity in SQLite

**Gate per Fase 3**: Sharpe ≥ 1.0 con max DD ≤ 15% sia in backtest che in
paper trading di 60 giorni. Se non si passa: tornare in Fase 2, NON andare live.

## Fase 3 — Live small (3–6 mesi dall'inizio)

Obiettivo: condizioni di mercato reali con poco capitale.

- [ ] Capitale iniziale: €200–500 in conto Alpaca live
- [ ] Limiti hard: `MAX_POSITION_PCT=0.10`, `DAILY_LOSS_LIMIT_PCT=0.02`
- [ ] Notifiche giornaliere (email/telegram) con riepilogo trade ed equity
- [ ] Review settimanale dei log + metriche
- [ ] Dashboard di monitoraggio (Streamlit o simile)

**Gate per Fase 4**: 3 mesi di live con metriche ≥ paper. Tolleranza:
underperformance massima del 30% rispetto al paper.

## Fase 4 — Scale (6–12 mesi)

- [ ] Aumento capitale graduale (+50% ogni mese in cui le metriche reggono)
- [ ] Multi-strategy allocator (suddividi il capitale tra strategie decorrelate)
- [ ] Hedging in regime di alta volatilità (filtro su VIX)

## Fase 5 — Target €500/mese (12–18 mesi)

- Capitale stimato per il target: **€25k–€40k** assumendo Sharpe ~1.0–1.5
  e rendimento netto reale 15–25% annuo (ottimistico ma non delirante).
- A questo punto: aggiungere strategie ML solo se dimostrano edge marginale.

## Cose che NON faremo (e perché)

- **No HFT/scalping**: latenza retail insufficiente, le commissioni mangiano l'edge.
- **No leva > 1.5x**: drawdown moltiplicato, rischio rovina reale.
- **No short selling iniziale**: costo di borrow + assignment risk; iniziamo long-only.
- **No penny stock**: pump & dump, slippage enorme.
- **No automazione del prelievo profitti**: i €500/mese li sposti tu, manualmente,
  solo quando l'equity > soglia configurata.
