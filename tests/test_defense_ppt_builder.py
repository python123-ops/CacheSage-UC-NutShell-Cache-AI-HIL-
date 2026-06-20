from __future__ import annotations

import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "reports" / "CacheSage-UC-defense-demo-NSFC.pptx"


class DefensePptBuilderTests(unittest.TestCase):
    def test_builder_uses_repository_background_and_evidence_data(self) -> None:
        source = (ROOT / "scripts" / "build_defense_ppt.mjs").read_text(encoding="utf-8")
        self.assertIn("assets", source)
        self.assertIn("defense-background.png", source)
        self.assertIn("rtl-functional-coverage.json", source)
        self.assertIn("sample-run-seed11.json", source)
        self.assertIn("review_journal.jsonl", source)
        self.assertNotIn('"34/36"', source)
        self.assertNotIn('"421"', source)

    def test_generated_deck_has_twelve_slides_and_embedded_background(self) -> None:
        self.assertTrue(PPTX.exists(), "请先运行 PPT 构建脚本")
        with zipfile.ZipFile(PPTX) as archive:
            slides = [
                name for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ]
            media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
        self.assertEqual(len(slides), 12)
        self.assertTrue(media)

    def test_visible_metrics_match_evidence(self) -> None:
        evidence = json.loads((ROOT / "reports" / "rtl-functional-coverage.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["coverage"]["covered"], 34)
        self.assertEqual(evidence["coverage"]["total"], 36)
        self.assertEqual(evidence["scoreboard"]["failures"], [])


if __name__ == "__main__":
    unittest.main()
