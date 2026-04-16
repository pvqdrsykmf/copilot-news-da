# 📋 Guida all'aggiornamento mensile

Questo documento spiega come aggiornare le novità Copilot ogni mese senza toccare il codice HTML.
**L'unico file da modificare è `data.json`.**

---

## Struttura del repository

```
copilot-news-da/
├── index.html       ← MAI toccare (codice presentazione)
├── data.json        ← ✅ SOLO QUESTO va aggiornato ogni mese
├── README.md        ← Documentazione tecnica GitHub
└── COME_AGGIORNARE.md ← Questa guida
```

---

## Come aggiornare `data.json` ogni mese

### Strumento consigliato
Apri `data.json` con un editor di testo. L'ideale è **Visual Studio Code** (gratuito), che colora la sintassi e ti avvisa se fai errori.
In alternativa puoi modificare direttamente su GitHub dal browser (vedi sotto).

---

## 1. Aggiornare le informazioni dell'edizione

All'inizio del file trovi:

```json
"meta": {
  "edition": "Febbraio – Aprile 2026",
  "updated": "16 aprile 2026",
  "alert": {
    "active": true,
    "text": "Testo del messaggio urgente in cima alla pagina."
  }
}
```

**Cosa fare ogni mese:**
- Cambia `"edition"` con il periodo dell'edizione (es. `"Maggio 2026"`)
- Cambia `"updated"` con la data di aggiornamento
- Se non c'è un messaggio urgente da mostrare: imposta `"active": false`
- Se c'è un messaggio urgente: imposta `"active": true` e scrivi il testo in `"text"`

---

## 2. Aggiungere una nuova scheda novità

Ogni scheda è un oggetto nella lista `"items"`. Copia questo template e compilalo:

```json
{
  "id": "nome-unico-senza-spazi",
  "app": "Teams",
  "cat": "c-teams",
  "ico": "🎬",
  "name": "Titolo della funzione (breve, max 8 parole)",
  "st": "avail",
  "isNew": true,
  "impact": "Descrizione dell'impatto per l'utente finale. Puoi usare <strong>testo in grassetto</strong>.",
  "example": "Un esempio pratico d'uso concreto, scritto in seconda persona.",
  "source": {
    "label": "Roadmap ID 558540",
    "url": "https://www.microsoft.com/en-us/microsoft-365/roadmap?id=558540",
    "note": "GA fine aprile – inizio maggio 2026"
  },
  "detail": {
    "steps": "1. Primo step.\n2. Secondo step.\n3. Terzo step.",
    "prompts": [
      "Primo prompt pronto da copiare.",
      "Secondo prompt pronto da copiare."
    ],
    "tips": [
      "Primo consiglio pratico.",
      "Secondo consiglio pratico."
    ]
  }
}
```

### Valori possibili per ogni campo

| Campo | Valori possibili | Significato |
|-------|-----------------|-------------|
| `app` | `"Word"`, `"Excel"`, `"PowerPoint"`, `"Outlook"`, `"Teams"`, `"Copilot Chat"` | App di riferimento |
| `cat` | `"c-word"`, `"c-excel"`, `"c-ppt"`, `"c-outlook"`, `"c-teams"`, `"c-chat"`, `"c-urgent"` | Colore della scheda |
| `st` | `"avail"`, `"soon"` | `avail` = disponibile ora, `soon` = in arrivo |
| `isNew` | `true`, `false` | Mostra o meno il badge "NUOVO" |

### Campo `source` — riferimento alla fonte ufficiale

Il campo `source` è opzionale ma fortemente consigliato. Mostra un link cliccabile in fondo a ogni scheda.

```json
"source": {
  "label": "Testo visibile del link (es. Roadmap ID 558540)",
  "url": "https://www.microsoft.com/en-us/microsoft-365/roadmap?id=558540",
  "note": "Nota breve sullo stato (es. GA marzo 2026)"
}
```

**Come trovare la fonte giusta:**

| Tipo di fonte | Quando usarla | Formato URL |
|---------------|--------------|-------------|
| **Roadmap ID** | Feature con ID noto — fonte più affidabile | `https://www.microsoft.com/en-us/microsoft-365/roadmap?id=XXXXXX` |
| **Message Center** | Feature annunciata via MC — accesso richiede Admin | `https://admin.microsoft.com` |
| **What's New blog** | Feature senza Roadmap ID | URL TechCommunity del post mensile |
| **Documentazione** | Feature già GA con doc stabile | URL learn.microsoft.com |

Se non hai la fonte, ometti il campo `source` del tutto — la scheda appare comunque senza link.

### Icone suggerite per app
- Word → 📝  Excel → 📊  PowerPoint → 🎨  Outlook → ✍️ 📆  Teams → 🎬 🎧 📋  Copilot Chat → 🧠 🔗 🤖 📎 📰

---

## 3. Aggiornare lo stato di una scheda esistente

Trova la scheda tramite il suo `"id"` e cambia il campo `"st"`:

```json
"st": "avail"   ← da "in arrivo" a "disponibile ora"
```

Ricorda di aggiornare anche `"impact"` e `"example"` per riflettere la nuova disponibilità.

---

## 4. Rimuovere una scheda obsoleta

Elimina l'intero blocco `{ ... }` che corrisponde alla scheda, comprese le virgole di separazione.

> ⚠️ **Attenzione alle virgole**: in JSON, gli elementi di una lista sono separati da virgole, tranne l'ultimo. Se rimuovi un elemento, assicurati che il precedente non abbia una virgola finale.

---

## 5. Aggiornare il piano editoriale

Il piano si trova nella sezione `"plan"` del file. Ogni settimana è:

```json
{
  "w": "W1",
  "d": "21–25 apr",
  "hot": false,
  "theme": "Titolo della newsletter di quella settimana",
  "tag": "Etichetta breve (es. Teams, Outlook, URGENTE)",
  "cov": "Novità in copertina · Separale con il punto medio ·",
  "note": "Note interne per il reparto creativo."
}
```

Imposta `"hot": true` solo per la settimana urgente (sfondo rosso).

---

## Come pubblicare su GitHub (aggiornamento dal browser)

1. Vai su `github.com/[tuo-account]/copilot-news-da`
2. Clicca su `data.json`
3. Clicca sull'icona ✏️ (matita) in alto a destra
4. Fai le modifiche nel browser
5. In basso, scrivi un messaggio tipo `"Aggiornamento maggio 2026"` e clicca **Commit changes**
6. Il sito si aggiorna automaticamente in 1–2 minuti

---

## Verificare che il JSON sia valido

Prima di fare commit, incolla il contenuto del file su **jsonlint.com** per verificare che non ci siano errori di sintassi (virgole mancanti, parentesi non chiuse, ecc.).

---

## Errori comuni

| Errore | Soluzione |
|--------|-----------|
| Pagina bianca dopo aggiornamento | Il JSON ha un errore di sintassi → verifica su jsonlint.com |
| Scheda non appare | Controlla che `"id"` sia unico e non contenga spazi |
| Testo con virgolette non funziona | Usa `\"` dentro le stringhe JSON invece di `"` |
| Badge "NUOVO" non scompare | Cambia `"isNew": true` in `"isNew": false` |
