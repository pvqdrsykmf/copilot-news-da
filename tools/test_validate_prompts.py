#!/usr/bin/env python3
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_prompts import validate

CATS = ["Riunioni & Teams", "Email & Outlook"]
def base_prompt(**kw):
    p = {"id": "x", "title": "t", "category": "Riunioni & Teams", "surface": "Teams",
         "output": "o", "summary": "s", "prompt_en": "en", "prompt_it": "it",
         "source": {"label": "PnP", "url": "https://github.com/..."}, "archived": False}
    p.update(kw); return p
def base_doc(prompts, cats=CATS):
    return {"meta": {"updated": "y", "source": "pnp/copilot-prompts"}, "categories": cats, "prompts": prompts}

class T(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(base_doc([base_prompt()])), [])
    def test_missing_field(self):
        p = base_prompt(); del p["prompt_it"]
        self.assertTrue(any("prompt_it" in e for e in validate(base_doc([p]))))
    def test_bad_category(self):
        p = base_prompt(category="Sconosciuta")
        self.assertTrue(any("category" in e for e in validate(base_doc([p]))))
    def test_missing_source_url(self):
        p = base_prompt(source={"label": "x"})
        self.assertTrue(any("source.url" in e for e in validate(base_doc([p]))))
    def test_duplicate_id(self):
        errs = validate(base_doc([base_prompt(id="d"), base_prompt(id="d")]))
        self.assertTrue(any("duplicato" in e for e in errs))

if __name__ == "__main__":
    unittest.main()
