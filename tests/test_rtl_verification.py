from __future__ import annotations

import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class RtlTransactionTests(unittest.TestCase):
    def test_write_uses_nutshell_simplebus_widths(self):
        from cachesage_uc.rtl_verification import RtlTransaction

        tx = RtlTransaction.write(
            0x2000,
            0x1122334455667788,
            mask=0b00110011,
            tag="same-set-write",
        )

        self.assertEqual(tx.address, 0x2000)
        self.assertEqual(tx.data, 0x1122334455667788)
        self.assertEqual(tx.mask, 0b00110011)
        self.assertEqual(tx.size, 7)

    def test_invalid_alignment_and_width_are_rejected(self):
        from cachesage_uc.rtl_verification import RtlTransaction

        with self.assertRaises(ValueError):
            RtlTransaction.read(0x4)
        with self.assertRaises(ValueError):
            RtlTransaction.write(0, 1 << 64)
        with self.assertRaises(ValueError):
            RtlTransaction.write(0, 0, mask=1 << 8)

    def test_same_set_stride_matches_rtl_index_bits(self):
        from cachesage_uc.rtl_verification import RTL_CACHE_CONFIG

        self.assertEqual(RTL_CACHE_CONFIG.line_size, 64)
        self.assertEqual(RTL_CACHE_CONFIG.sets, 128)
        self.assertEqual(RTL_CACHE_CONFIG.ways, 4)
        self.assertEqual(RTL_CACHE_CONFIG.same_set_stride, 0x2000)
        self.assertEqual(RTL_CACHE_CONFIG.set_index(0x0000), 0)
        self.assertEqual(RTL_CACHE_CONFIG.set_index(0x2000), 0)


class RtlScoreboardTests(unittest.TestCase):
    def test_reference_memory_applies_eight_byte_mask(self):
        from cachesage_uc.rtl_verification import RtlReferenceMemory, RtlTransaction

        reference = RtlReferenceMemory()
        reference.apply(RtlTransaction.write(0, 0x1122334455667788))
        reference.apply(RtlTransaction.write(0, 0xFFEEDDCCBBAA0099, mask=0x0F))

        self.assertEqual(reference.read(0), 0x11223344BBAA0099)

    def test_scoreboard_records_read_mismatch_with_seed_and_index(self):
        from cachesage_uc.rtl_verification import RtlScoreboard, RtlTransaction

        scoreboard = RtlScoreboard()
        write = RtlTransaction.write(0, 0xAABBCCDDEEFF0011, tag="warm")
        read = RtlTransaction.read(0, tag="readback")
        scoreboard.observe(write, observed_data=None, seed=11, index=0)
        scoreboard.observe(read, observed_data=0, seed=11, index=1)

        self.assertEqual(scoreboard.comparisons, 1)
        self.assertEqual(len(scoreboard.failures), 1)
        self.assertEqual(scoreboard.failures[0]["seed"], 11)
        self.assertEqual(scoreboard.failures[0]["index"], 1)
        self.assertIn("AABBCCDDEEFF0011", scoreboard.failures[0]["message"])


class _FakeSimpleBusAgent:
    def __init__(self):
        self.requests = []
        self.responses = [{"rdata": 0x1234, "cmd": 6}]

    async def send_req(self, *args):
        self.requests.append(args)

    async def get_resp(self):
        return self.responses.pop(0)


class NutShellRequestDriverTests(unittest.IsolatedAsyncioTestCase):
    async def test_write_passes_size_mask_and_data_in_protocol_order(self):
        from cachesage_uc.adapters.nutshell_runtime import NutShellRequestDriver
        from cachesage_uc.rtl_verification import RtlTransaction

        agent = _FakeSimpleBusAgent()
        driver = NutShellRequestDriver(agent, read_cmd=0, write_cmd=1)
        transaction = RtlTransaction.write(0x1000, 0x1122334455667788, mask=0x5A)

        response = await driver.execute(transaction)

        self.assertEqual(agent.requests, [(0x1000, 7, 1, 0x5A, 0x1122334455667788)])
        self.assertEqual(response["rdata"], 0x1234)


class RtlCoverageTests(unittest.TestCase):
    def test_catalog_has_fixed_36_real_dut_points(self):
        from cachesage_uc.rtl_coverage import RTL_COVERPOINTS

        self.assertEqual(len(RTL_COVERPOINTS), 36)
        self.assertIn("rtl_dirty_eviction_writeback", RTL_COVERPOINTS)
        self.assertIn("rtl_victim_way_3", RTL_COVERPOINTS)
        self.assertIn("rtl_probe_hit_dirty", RTL_COVERPOINTS)
        self.assertIn("rtl_idle_empty", RTL_COVERPOINTS)

    def test_report_requires_threshold_and_zero_failures(self):
        from cachesage_uc.rtl_coverage import RtlCoverageCollector

        collector = RtlCoverageCollector()
        for point in list(collector.points)[:33]:
            collector.hit(point, source="unit-test")

        report = collector.report(scoreboard_comparisons=384, scoreboard_failures=[])

        self.assertEqual(report.covered, 33)
        self.assertEqual(report.total, 36)
        self.assertEqual(report.percent, 91.67)
        self.assertEqual(report.status, "rtl_functional_coverage_complete")

        failed = collector.report(
            scoreboard_comparisons=384,
            scoreboard_failures=[{"message": "mismatch"}],
        )
        self.assertEqual(failed.status, "rtl_functional_coverage_failed")

    def test_observations_drive_coverage_hits(self):
        from cachesage_uc.rtl_coverage import RtlCoverageCollector, RtlObservation

        collector = RtlCoverageCollector()
        collector.observe(
            RtlObservation(
                op="read",
                address=0,
                mask=0xFF,
                hit=False,
                memory_read=True,
                refill=True,
                victim_way=0b0001,
                source="seed-11:0",
            )
        )
        collector.observe(
            RtlObservation(
                op="write",
                address=0,
                mask=0x0F,
                hit=True,
                dirty_eviction=True,
                writeback=True,
                probe_result="dirty_hit",
                source="seed-11:1",
            )
        )

        self.assertGreater(collector.points["rtl_read_miss_refill"].hit_count, 0)
        self.assertGreater(collector.points["rtl_write_hit"].hit_count, 0)
        self.assertGreater(collector.points["rtl_partial_mask_low"].hit_count, 0)
        self.assertGreater(collector.points["rtl_dirty_eviction_writeback"].hit_count, 0)
        self.assertGreater(collector.points["rtl_probe_hit_dirty"].hit_count, 0)


if __name__ == "__main__":
    unittest.main()
