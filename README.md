# Copilot Novità — Digital Attitude

Pagina web interattiva per monitorare e comunicare le novità mensili di Microsoft 365 Copilot al team creativo e ai clienti.

## Come funziona

| File | Ruolo |
|------|-------|
| `index.html` | Presentazione (CSS + JS) — **non modificare** |
| `data.json` | Contenuti — **aggiornare ogni mese** |
| `COME_AGGIORNARE.md` | Guida operativa per il reparto creativo |

## Setup GitHub Pages (prima volta)

1. Fai il fork o crea un nuovo repository su GitHub
2. Carica tutti e 3 i file (`index.html`, `data.json`, `COME_AGGIORNARE.md`)
3. Vai su **Settings → Pages**
4. In "Source" seleziona `Deploy from a branch`
5. Scegli il branch `main` e la cartella `/ (root)`
6. Clicca **Save**
7. Dopo 1–2 minuti il sito è online all'indirizzo `https://[username].github.io/[repo-name]`

## Aggiornamento mensile

Modifica solo `data.json` — vedi `COME_AGGIORNARE.md` per istruzioni dettagliate.

## Funzionalità

- Filtri per app (Word, Excel, PowerPoint, Outlook, Teams, Copilot Chat)
- Filtri per stato (Disponibile ora / In arrivo)
- Ricerca testuale
- Pannello approfondimento per ogni scheda (step, prompt copiabili, consigli)
- Sistema di flag per archiviare le novità già pubblicate
- Tab "Già pubblicate" con data di archiviazione e opzione ripristino
- Piano editoriale settimanale
- Stato di pubblicazione persistente (localStorage per browser)
