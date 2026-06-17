# Knowledge Base — Imprenditoria AI

Base di conoscenza che alimenta un **agente esperto di imprenditoria nell'AI**.
Raccoglie e struttura contenuti (trascrizioni di video, articoli, talk, note)
in modo che siano facilmente consultabili sia da una persona sia da un agente AI.

## Struttura

```
kb/
├── README.md            # questo file: indice e convenzioni
├── template-fonte.md    # template da copiare per ogni nuova fonte
└── fonti/               # una scheda .md per ogni fonte (video, articolo, talk…)
```

## Come aggiungere una fonte

1. Copia `template-fonte.md` in `fonti/` con un nome-file descrittivo
   (es. `2026-06-overhang-imprenditoria-ai.md`).
2. Compila il front-matter (metadati) e le sezioni.
3. Incolla la trascrizione/contenuto grezzo nella sezione *Trascrizione*.
4. Estrai concetti, insight azionabili e citazioni nelle rispettive sezioni.
5. Aggiungi la fonte all'**Indice** qui sotto.

## Convenzioni per l'agente

Ogni scheda fonte usa un front-matter YAML con campi standard, così l'agente
può filtrare per tag, stato, tipo e data. Le sezioni sono sempre le stesse
(Sintesi → Concetti chiave → Insight azionabili → Citazioni → Trascrizione)
per dare struttura prevedibile al retrieval.

`status` può essere: `bozza`, `trascrizione-mancante`, `completo`.

## Indice fonti

| Fonte | Tipo | Stato | Tag principali |
|-------|------|-------|----------------|
| [Overhang — il divario di capacità dell'AI](fonti/2026-06-overhang-imprenditoria-ai.md) | video YouTube | trascrizione-mancante | overhang, adozione-ai, vantaggio-competitivo |
