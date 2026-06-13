from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "cachesage_uc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_plan_command_outputs_machine_readable_scenarios(self):
        result = run_cli("plan")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["title"], "CacheSage-UC NutShell Cache Verification Plan")
        self.assertGreaterEqual(len(payload["scenarios"]), 8)
        self.assertTrue(
            any("dirty eviction" in item["name"].lower() for item in payload["scenarios"])
        )


    def test_report_command_writes_markdown_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.md"
            result = run_cli("report", "--output", str(output))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("wrote", result.stdout.lower())
            text = output.read_text(encoding="utf-8")
            self.assertIn("CacheSage-UC Initial Verification Report", text)
            self.assertIn("AI 缺陷与人工修正对比表", text)


if __name__ == "__main__":
    unittest.main()
