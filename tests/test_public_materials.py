from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = [
    ROOT / "README.md",
    ROOT / "docs",
    ROOT / "reports",
    ROOT / "examples",
    ROOT / "review_journal.jsonl",
]
BANNED_PUBLIC_PHRASES = [
    "Why This Project",
    "score well",
    "competition dimension",
    "AI usage efficiency",
    "AI output",
    "AI blind spot",
    "AI defect",
    "AI-generated report",
    "AI-HIL",
    "AI 盲区",
    "拿高分",
    "高分",
    "first prize",
    "First-Prize",
    "C:\\Users\\",
    "px830",
]


class PublicMaterialsToneTests(unittest.TestCase):
    def test_public_materials_avoid_marketing_and_obvious_generation_terms(self):
        violations = []
        for path in _iter_public_files():
            text = path.read_text(encoding="utf-8")
            for phrase in BANNED_PUBLIC_PHRASES:
                if phrase.lower() in text.lower():
                    violations.append(f"{path.relative_to(ROOT)}: {phrase}")

        self.assertEqual(violations, [])

    def test_old_review_artifact_names_are_removed(self):
        self.assertFalse((ROOT / "ai_hil_log.jsonl").exists())
        self.assertFalse((ROOT / "docs" / "ai-defect-catalog.md").exists())
        self.assertFalse((ROOT / "docs" / "ai-human-collaboration.md").exists())
        self.assertTrue((ROOT / "review_journal.jsonl").exists())
        self.assertTrue((ROOT / "docs" / "review-catalog.md").exists())
        self.assertTrue((ROOT / "docs" / "review-workflow.md").exists())


def _iter_public_files():
    for path in PUBLIC_PATHS:
        if path.is_file():
            yield path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in {".md", ".json", ".jsonl"}:
                    yield child


if __name__ == "__main__":
    unittest.main()
