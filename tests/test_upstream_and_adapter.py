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
sys.path.insert(0, str(SRC))


class UpstreamLockTests(unittest.TestCase):
    def test_upstream_lock_pins_example_nutshell_cache(self):
        lock = json.loads((ROOT / "upstream.lock.json").read_text(encoding="utf-8"))

        self.assertEqual(lock["name"], "Example-NutShellCache")
        self.assertEqual(lock["repo"], "XS-MLVP/Example-NutShellCache")
        self.assertEqual(lock["remote"], "https://github.com/XS-MLVP/Example-NutShellCache.git")
        self.assertRegex(lock["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(lock["required_paths"], ["Makefile", "rtl", "src", "test"])

    def test_fetch_script_dry_run_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "fetch_upstream_example.py"),
                    "--lock",
                    str(ROOT / "upstream.lock.json"),
                    "--dest",
                    str(Path(tmp) / "Example-NutShellCache"),
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["repo"], "XS-MLVP/Example-NutShellCache")
        self.assertIn("git clone", payload["commands"][0])


class NutShellAdapterTests(unittest.TestCase):
    def test_example_layout_reports_required_paths(self):
        from cachesage_uc.adapters.nutshell_example import inspect_example_tree

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Makefile").write_text(
                "PYTHONPATH=.\n.PHONY: gen_dut test\n\ngen_dut:\n\t@echo ok\n",
                encoding="utf-8",
            )
            for dirname in ("rtl", "src", "test"):
                (root / dirname).mkdir()

            layout = inspect_example_tree(root)

        self.assertTrue(layout.ready)
        self.assertEqual(layout.missing_paths, [])
        self.assertEqual(layout.make_targets["gen_dut"], "Generate Picker/Toffee software DUT")
        self.assertNotIn(".PHONY", layout.make_targets)
        self.assertNotIn("PYTHONPATH=.", layout.make_targets)
        self.assertIn("rtl", layout.to_dict()["present_paths"])

    def test_example_layout_explains_missing_paths(self):
        from cachesage_uc.adapters.nutshell_example import inspect_example_tree

        with tempfile.TemporaryDirectory() as tmp:
            layout = inspect_example_tree(Path(tmp))

        self.assertFalse(layout.ready)
        self.assertIn("Makefile", layout.missing_paths)
        self.assertIn("Run scripts/fetch_upstream_example.py", layout.hint)

    def test_transaction_maps_to_toffee_case(self):
        from cachesage_uc.adapters.toffee_bridge import to_toffee_case
        from cachesage_uc.verification import Transaction

        case = to_toffee_case(Transaction.write(0x20, 0xAABBCCDD, mask=0b0011, tag="masked-hit"))

        self.assertEqual(case["channel"], "cache_req")
        self.assertEqual(case["op"], "write")
        self.assertEqual(case["addr"], 0x20)
        self.assertEqual(case["data"], 0xAABBCCDD)
        self.assertEqual(case["mask"], 0b0011)
        self.assertEqual(case["meta"]["tag"], "masked-hit")

    def test_smoke_reports_missing_dependencies_for_ready_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "Example-NutShellCache"
            upstream.mkdir()
            (upstream / "Makefile").write_text("gen_dut:\n\t@echo gen\n\ntest:\n\t@echo test\n", encoding="utf-8")
            for dirname in ("rtl", "src", "test"):
                (upstream / dirname).mkdir()
            output = root / "smoke.json"
            markdown = root / "smoke.md"
            env = os.environ.copy()
            env["PATH"] = ""

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_nutshell_smoke.py"),
                    "--upstream",
                    str(upstream),
                    "--output",
                    str(output),
                    "--markdown",
                    str(markdown),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "missing_dependencies")
            self.assertIn("picker", payload["missing_dependencies"])
            self.assertIn("install", payload["next_command"].lower())


class ReviewEvidenceTests(unittest.TestCase):
    def test_review_journal_has_required_human_review_fields(self):
        rows = [
            json.loads(line)
            for line in (ROOT / "review_journal.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            self.assertTrue(row["prompt"])
            self.assertTrue(row["draft_summary"])
            self.assertTrue(row["review_finding"])
            self.assertTrue(row["correction"])
            self.assertTrue(row["linked_evidence"])
            self.assertIn("coverage_delta", row)
            self.assertNotIn("ai_output_summary", row)
            self.assertNotIn("human_finding", row)


if __name__ == "__main__":
    unittest.main()
