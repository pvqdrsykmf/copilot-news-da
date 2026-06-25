#!/usr/bin/env python3
"""Scarica le cartelle PnP samples/prompts, filtra M365-only, parserizza i README.
Emette su stdout un JSON bozza con i campi DETERMINISTICI; l'arricchimento
(prompt_it, category, output, title-IT) è aggiunto a valle dall'agente/routine."""
import json, sys, urllib.request
from curate_prompts import parse_readme, infer_surface, is_included

API = "https://api.github.com/repos/pnp/copilot-prompts/contents/samples/prompts"
RAW_UPPER = "https://raw.githubusercontent.com/pnp/copilot-prompts/main/samples/prompts/{}/README.md"
RAW_LOWER = "https://raw.githubusercontent.com/pnp/copilot-prompts/main/samples/prompts/{}/readme.md"

def _get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "da-copilot-news"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read().decode("utf-8")
    return data if raw else json.loads(data)

def _get_readme(name):
    """Try README.md first, then readme.md."""
    for template in (RAW_UPPER, RAW_LOWER):
        try:
            return _get(template.format(name), raw=True)
        except Exception:
            pass
    return None

def main():
    folders = [x["name"] for x in _get(API) if x["type"] == "dir" and is_included(x["name"])]
    out = []
    for name in folders:
        md = _get_readme(name)
        if md is None:
            print(f"skip {name}: no README found", file=sys.stderr); continue
        p = parse_readme(md)
        out.append({
            "id": name,
            "title": p["title"],
            "surface": infer_surface(p["instructions"]),
            "summary": p["summary"][:400],
            "prompt_en": p["prompt_en"],
            "source": {"label": "PnP sample",
                       "url": f"https://github.com/pnp/copilot-prompts/tree/main/samples/prompts/{name}"},
        })
    print(json.dumps({"draft": out, "count": len(out)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
