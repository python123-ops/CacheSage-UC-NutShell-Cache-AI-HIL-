from __future__ import annotations

import re
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
    "中文简介",
    "Next Integration",
    "Next Regression",
    "Remaining Integration Work",
    "Not claimed yet",
    "Pending",
    "Next command",
    "next checkpoint",
    "下一个",
    "下一步",
    "待完成",
    "未完成",
    "AI 盲区",
    "拿高分",
    "高分",
    "first prize",
    "First-Prize",
    "C:\\Users\\",
    "px830",
]
MOJIBAKE_MARKERS = ["涓", "锛", "銆", "鐩", "璁", "鏁", "鎷", "楂"]
ALLOWED_NON_CHINESE_HEADINGS = {"# CacheSage-UC"}


class PublicMaterialsToneTests(unittest.TestCase):
    def test_public_materials_avoid_marketing_and_obvious_generation_terms(self):
        violations = []
        for path in _iter_public_files():
            text = path.read_text(encoding="utf-8")
            for phrase in BANNED_PUBLIC_PHRASES:
                if phrase.lower() in text.lower():
                    violations.append(f"{path.relative_to(ROOT)}: {phrase}")

        self.assertEqual(violations, [])

    def test_public_materials_have_no_mojibake_markers(self):
        violations = []
        for path in _iter_public_files():
            text = path.read_text(encoding="utf-8")
            for marker in MOJIBAKE_MARKERS:
                if marker in text:
                    violations.append(f"{path.relative_to(ROOT)}: {marker}")

        self.assertEqual(violations, [])

    def test_markdown_headings_are_chinese_engineering_notes(self):
        violations = []
        han_pattern = re.compile(r"[\u4e00-\u9fff]")
        for path in _iter_public_files():
            if path.suffix != ".md":
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = line.strip()
                if not stripped.startswith("#"):
                    continue
                if stripped in ALLOWED_NON_CHINESE_HEADINGS:
                    continue
                if not han_pattern.search(stripped):
                    violations.append(f"{path.relative_to(ROOT)}:{lineno}: {stripped}")

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
