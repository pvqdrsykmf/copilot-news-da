# Regole di curation — Copilot News DA

## Sync settimanale dei Prompt (`prompts.json`)
Fonte UNICA: `pnp/copilot-prompts` → `samples/prompts` (nessun'altra fonte).
1. Scarica `prompts.json`, `tools/curate_prompts.py`, `tools/fetch_and_parse_prompts.py`,
   `tools/validate_prompts.py` dal repo (via API).
2. `python3 tools/fetch_and_parse_prompts.py > draft.json` → lista cartelle M365-only (filtro
   `EXCLUDE_SUBSTRINGS`).
3. **Incrementale:**
   - cartella NUOVA (id non in `prompts.json`) → arricchisci (prompt_it, category ∈ lista,
     output, title) e **aggiungi**;
   - cartella SPARITA (id presente ma non più nel repo) → imposta `archived: true` (non eliminare);
   - cartella GIÀ presente → **non ri-curare** (stabilità categorie/traduzioni).
4. Aggiorna `meta.updated` e `meta.count`. Valida: `python3 tools/validate_prompts.py prompts.json`.
   Se fallisce, NON pubblicare.
5. Pubblica `prompts.json` con lo stesso meccanismo di `data.json` (commit/push → Cloudflare).
Categorie ammesse: Email & Outlook · Riunioni & Teams · Documenti (Word) · Dati & Excel ·
Presentazioni (PowerPoint) · Produttività & pianificazione · HR & People · Analisi & report · Altro.
