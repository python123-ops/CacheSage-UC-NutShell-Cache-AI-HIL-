from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_verification_pdf.py"
BANNED_REPORT_PHRASES = [
    "高分",
    "拿奖",
    "AI output",
    "AI blind spot",
    "Next command",
    "Pending",
    "C:\\Users\\",
    "px830",
]
MOJIBAKE_MARKERS = ["涓", "锛", "銆", "鐩", "璁", "鏁", "鎷", "楂"]


class VerificationPdfReportTests(unittest.TestCase):
    def test_report_builder_generates_submission_markdown_and_tex(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output-dir",
                    str(output_dir),
                    "--skip-pdf",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output_dir / "CacheSage-UC-verification-report.md"
            tex = output_dir / "CacheSage-UC-verification-report.tex"
            self.assertTrue(markdown.exists())
            self.assertTrue(tex.exists())

            md_text = markdown.read_text(encoding="utf-8")
            tex_text = tex.read_text(encoding="utf-8")
            normalized_tex = tex_text.replace("\\%", "%").replace("\\_", "_")
            for text in (md_text, normalized_tex):
                self.assertIn("CacheSage-UC：面向 NutShell Cache 的 UCAgent 辅助自动化验证报告", text)
                self.assertIn("23/23", text)
                self.assertIn("100.00%", text)
                self.assertIn("drop_dirty_writeback", text)
                self.assertIn("unstable_under_stall", text)
                self.assertIn("RTL artifact", text)
                self.assertIn("RTL code coverage", text)
                self.assertIn("不声称已发现真实 NutShell RTL bug", text)
                self.assertNotIn("Why This Project", text)
                for phrase in BANNED_REPORT_PHRASES:
                    self.assertNotIn(phrase, text)
                for marker in MOJIBAKE_MARKERS:
                    self.assertNotIn(marker, text)

            self.assertIn("\\tableofcontents", tex_text)
            self.assertIn("\\begin{tikzpicture}", tex_text)


if __name__ == "__main__":
    unittest.main()
