from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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
        self.assertEqual(payload["title"], "CacheSage-UC NutShell Cache 验证计划")
        self.assertGreaterEqual(len(payload["scenarios"]), 8)
        self.assertTrue(any("dirty eviction" in item["name"].lower() for item in payload["scenarios"]))

    def test_report_command_writes_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.md"
            result = run_cli("report", "--output", str(output))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("wrote", result.stdout.lower())
            text = output.read_text(encoding="utf-8")
            self.assertIn("CacheSage-UC 验证记录", text)
            self.assertIn("设计复盘与修正记录", text)
            self.assertIn("故障注入记录", text)
            self.assertNotIn("AI output", text)
            self.assertNotIn("AI 盲区", text)
            self.assertNotIn("Next", text)
            self.assertNotIn("Pending", text)

    def test_fault_run_uses_deterministic_detecting_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "fault.json"
            result = run_cli(
                "run",
                "--seed",
                "11",
                "--count",
                "16",
                "--fault",
                "refill_shift",
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(payload["passed"])
            self.assertTrue(any("data mismatch" in item["message"].lower() for item in payload["failures"]))


if __name__ == "__main__":
    unittest.main()
