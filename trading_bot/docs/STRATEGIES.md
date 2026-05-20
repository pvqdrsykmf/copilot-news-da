# Strategie

## 1. Momentum cross-sectional

**File**: `src/trading_bot/strategies/momentum.py`

**Logica**: ogni ~mese, classifica gli asset dell'universo per rendimento
sui passati 6 mesi (escludendo l'ultimo mese per evitare il bias di
short-term reversal). Compra equal-weight i top N.

**Parametri di default**:
- `lookback_days = 126` (~6 mesi)
- `skip_days = 21` (~1 mese)
- `n_top = 3`
- `rebalance_days = 21`
- `min_momentum = 0.0` (solo se in trend positivo)

**Edge**: documentato in letteratura da Jegadeesh & Titman (1993). Funziona
meglio su ETF settoriali liquidi.

**Quando rompe**: regime change improvvisi (es. Marzo 2020). Mitigato da
rebalance frequente + circuit breaker.

## 2. Mean reversion (RSI estremi)

**File**: `src/trading_bot/strategies/mean_reversion.py`

**Logica**: compra asset liquidi (mega-cap, indici) quando l'RSI(2) scende
sotto 10, vendi quando torna sopra 70. Filtro di trend: solo se prezzo > SMA200
(no catching falling knives).

**Parametri di default**:
- `rsi_period = 2`
- `oversold = 10.0`
- `exit_rsi = 70.0`
- `trend_filter_sma = 200`
- `max_concurrent = 5`

**Edge**: documentato da Larry Connors. Funziona bene su S&P 500 dal 2000+,
specialmente in regime laterale/rialzista moderato.

**Quando rompe**: trend ribassisti forti — il filtro SMA200 protegge ma non
in caso di gap improvviso (es. shock geopolitici).

## Idee future (non implementate)

### Crypto momentum (alta vol, 24/7)
- Universe: top 10 crypto su Alpaca
- Rebalance giornaliero invece che mensile (la vol è 3x maggiore)
- Stessa logica momentum, ma con `lookback_days = 30`, `n_top = 3`

### Pairs trading (market-neutral)
- Asset cointegrati (es. KO/PEP, V/MA, XLE vs WTI)
- Z-score della spread; entry quando |z| > 2, exit quando |z| < 0.5
- Edge: market-neutral, Sharpe storicamente buono ma capacity limitata

### Volatility-targeted sizing
- Modifica al sizer: riduci esposizione quando la realized vol > target
- Riduce drawdown senza sacrificare troppo CAGR

### ML ensemble (fase 2+)
- Feature: momentum multi-scala, RSI, MACD, vol realizzata, breadth di mercato
- Modello: gradient boosting (LightGBM) o piccolo MLP
- Output: probabilità di rendimento positivo a 5/20 giorni
- ⚠️ Va validato con walk-forward severo; ML è il regno dell'overfitting
