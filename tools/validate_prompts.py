#!/usr/bin/env python3
"""Validatore schema per prompts.json di copilot-news-da."""
import json, sys

REQUIRED = ["id", "title", "category", "surface", "output", "summary", "prompt_en", "prompt_it", "source"]

def validate(data):
    errors = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta mancante o non oggetto")
    elif not isinstance(meta.get("updated"), str) or not meta.get("updated"):
        errors.append("meta.updated mancante/non stringa")
    cats = data.get("categories")
    if not isinstance(cats, list) or not cats:
        errors.append("categories mancante o vuoto"); cats = []
    prompts = data.get("prompts")
    if not isinstance(prompts, list):
        errors.append("prompts mancante o non lista"); return errors
    seen = set()
    for i, p in enumerate(prompts):
        where = f"prompts[{i}]"
        if not isinstance(p, dict):
            errors.append(f"{where} non oggetto"); continue
        pid = p.get("id"); where = f"prompt '{pid}'" if pid else where
        for f in REQUIRED:
            if not p.get(f):
                errors.append(f"{where}: campo obbligatorio mancante/vuoto '{f}'")
        if pid in seen:
            errors.append(f"{where}: id duplicato")
        seen.add(pid)
        if cats and p.get("category") and p["category"] not in cats:
            errors.append(f"{where}: category '{p.get('category')}' non in categories")
        src = p.get("source")
        if not isinstance(src, dict) or not src.get("url"):
            errors.append(f"{where}: source.url mancante")
    return errors

def main(argv):
    if len(argv) < 2:
        print("uso: validate_prompts.py <prompts.json>"); return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON non valido: {e}"); return 1
    errors = validate(data)
    if errors:
        print(f"❌ {len(errors)} errori:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"✅ prompts.json valido — {len(data['prompts'])} prompt")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
