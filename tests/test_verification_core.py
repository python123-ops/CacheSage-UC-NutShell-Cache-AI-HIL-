from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


class VerificationCoreTests(unittest.TestCase):
    def test_masked_write_preserves_unselected_bytes(self):
        from cachesage_uc.verification import CacheConfig, CacheModel, Transaction

        cache = CacheModel(CacheConfig(line_size=16, sets=2, ways=2))
        cache.write_memory_word(0x20, 0x11223344)

        cache.apply(Transaction.write(address=0x20, data=0xAABBCCDD, mask=0b0011, tag="masked"))
        result = cache.apply(Transaction.read(address=0x20, tag="readback"))

        self.assertEqual(result.data, 0x1122CCDD)

    def test_dirty_eviction_writes_victim_to_memory(self):
        from cachesage_uc.verification import CacheConfig, CacheModel, Transaction

        cache = CacheModel(CacheConfig(line_size=16, sets=1, ways=1))

        cache.apply(Transaction.write(address=0x00, data=0xDEADBEEF, mask=0b1111, tag="dirty"))
        cache.apply(Transaction.read(address=0x10, tag="evict"))

        self.assertEqual(cache.read_memory_word(0x00), 0xDEADBEEF)
        self.assertTrue(any(event.kind == "writeback" and event.address == 0x00 for event in cache.events))

    def test_scoreboard_detects_dropped_dirty_writeback_fault(self):
        from cachesage_uc.verification import FaultMode, VerificationRunner, build_directed_eviction_sequence

        result = VerificationRunner().run(
            build_directed_eviction_sequence(),
            fault=FaultMode.DROP_DIRTY_WRITEBACK,
        )

        self.assertFalse(result.passed)
        self.assertGreaterEqual(len(result.failures), 1)
        self.assertIn("memory mismatch", result.failures[0].message.lower())
        self.assertIn("cp_dirty_eviction", result.covered_points)

    def test_each_fault_mode_has_a_deterministic_detecting_sequence(self):
        from cachesage_uc.verification import FaultMode, VerificationRunner, build_fault_sequence

        expected_markers = {
            FaultMode.DROP_DIRTY_WRITEBACK: "memory mismatch",
            FaultMode.IGNORE_WRITE_MASK: "data mismatch",
            FaultMode.STUCK_REPLACEMENT: "eviction sequence mismatch",
            FaultMode.REFILL_SHIFT: "data mismatch",
            FaultMode.UNSTABLE_UNDER_STALL: "data mismatch",
        }

        runner = VerificationRunner()
        for fault, marker in expected_markers.items():
            with self.subTest(fault=fault.value):
                sequence = build_fault_sequence(fault)
                result = runner.run(sequence, fault=fault)

                self.assertFalse(result.passed)
                self.assertGreaterEqual(len(result.failures), 1)
                joined = "\n".join(failure.message.lower() for failure in result.failures)
                self.assertIn(marker, joined)

    def test_seeded_random_run_is_reproducible_and_reaches_core_coverage(self):
        from cachesage_uc.verification import ALL_COVERPOINTS, VerificationRunner, build_seeded_random_sequence

        sequence_a = build_seeded_random_sequence(seed=11, count=96)
        sequence_b = build_seeded_random_sequence(seed=11, count=96)
        self.assertEqual([txn.to_dict() for txn in sequence_a], [txn.to_dict() for txn in sequence_b])

        result = VerificationRunner().run(sequence_a)

        self.assertTrue(result.passed, result.failures)
        self.assertGreaterEqual(len(ALL_COVERPOINTS), 20)
        self.assertGreaterEqual(result.coverage.percent, 90.0)
        self.assertIn("cp_read_miss_refill", result.covered_points)
        self.assertIn("cp_write_hit_mask", result.covered_points)
        self.assertIn("cp_replacement_rotation", result.covered_points)


class VerificationCliTests(unittest.TestCase):
    def test_run_command_writes_json_result(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cachesage_uc.cli",
                    "run",
                    "--seed",
                    "11",
                    "--count",
                    "48",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["seed"], 11)
            self.assertGreaterEqual(payload["coverage"]["total"], 20)
            self.assertGreaterEqual(payload["coverage"]["percent"], 90.0)


if __name__ == "__main__":
    unittest.main()
