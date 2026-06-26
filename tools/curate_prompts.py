#!/usr/bin/env python3
"""Parser deterministico dei README dei prompt PnP -> record strutturato.
La parte LLM (prompt_it, category, output, title-IT) viene aggiunta a valle (vedi CURATION.md)."""
import re

SECTION_RE = re.compile(r'^(#{1,6})\s+(.*)$', re.M)

def _strip_emoji(s):
    s = re.sub(r'[\U0001F000-\U0001FAFF←-➿️☀-⛿]', '', s)
    return s.strip(' #').strip()

def split_sections(md):
    """{heading_normalizzato_lower: testo} per ogni heading."""
    parts, matches = {}, list(SECTION_RE.finditer(md))
    for i, m in enumerate(matches):
        name = _strip_emoji(m.group(2)).lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        parts[name] = md[start:end].strip()
    return parts

def parse_readme(md):
    secs = split_sections(md)
    h1 = next((m.group(2) for m in SECTION_RE.finditer(md) if len(m.group(1)) == 1), '')
    return {
        "title": _strip_emoji(h1),
        "summary": secs.get("summary", ""),
        "prompt_en": secs.get("prompt", "").strip(),
        "instructions": secs.get("instructions", ""),
        "prerequisites": secs.get("prerequisites", ""),
    }

SURFACE_KEYWORDS = [
    ("Teams", ["teams"]), ("Outlook", ["outlook"]), ("Word", ["word"]),
    ("Excel", ["excel"]), ("PowerPoint", ["powerpoint"]), ("Loop", ["loop"]),
    ("Business Chat", ["business chat", "copilot chat", "microsoft 365 copilot chat", "copilot app", "m365 chat"]),
]
def infer_surface(instructions):
    t = (instructions or "").lower()
    hits = [name for name, kws in SURFACE_KEYWORDS if any(k in t for k in kws)]
    # Filter out Business Chat if other surfaces are found
    if hits and len(hits) > 1 and "Business Chat" in hits:
        hits = [h for h in hits if h != "Business Chat"]
    return " / ".join(dict.fromkeys(hits)) if hits else "Business Chat"

EXCLUDE_SUBSTRINGS = ["github-", "powershell", "powerplatform", "patchfunction",
                      "asp-dot-net", "azure-devops", "adaptivecard", "fix-code"]
def is_included(folder_name):
    f = (folder_name or "").lower()
    return not any(s in f for s in EXCLUDE_SUBSTRINGS)
