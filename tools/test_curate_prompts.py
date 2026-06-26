#!/usr/bin/env python3
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curate_prompts import parse_readme, infer_surface, is_included

README = """
# 🚀 Draft Actionable Tasks 📄

## Summary
This prompt drafts meeting summaries and Planner tasks.

## Prompt 💡

Analyze the most recent email with the subject "Meeting Planning" and summarize the key points.

### Description ℹ️
Saves time on follow-ups.

## Instructions 📝
1. Open the Microsoft Teams app.
2. Access the Copilot app within Teams.

## Prerequisites
- Copilot for Microsoft 365
"""

class T(unittest.TestCase):
    def test_title_stripped(self):
        self.assertEqual(parse_readme(README)["title"], "Draft Actionable Tasks")
    def test_prompt_block_only(self):
        p = parse_readme(README)["prompt_en"]
        self.assertIn("Analyze the most recent email", p)
        self.assertNotIn("Saves time", p)        # si ferma prima di ### Description
        self.assertNotIn("Open the Microsoft Teams", p)
    def test_summary(self):
        self.assertIn("Planner tasks", parse_readme(README)["summary"])
    def test_surface_teams(self):
        self.assertEqual(infer_surface(parse_readme(README)["instructions"]), "Teams")
    def test_surface_default(self):
        self.assertEqual(infer_surface("nessun riferimento app"), "Business Chat")
    def test_include_exclude(self):
        self.assertTrue(is_included("m365-actionable-meeting-summary"))
        self.assertFalse(is_included("github-powershell-prompt"))
        self.assertFalse(is_included("m365-azure-devops-pipeline-prompt"))

if __name__ == "__main__":
    unittest.main()
