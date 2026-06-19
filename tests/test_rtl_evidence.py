import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cachesage_uc.rtl_coverage import RtlCoverageCollector
from cachesage_uc.rtl_evidence import (
    build_rtl_evidence,
    parse_verilator_coverage_summary,
    render_rtl_markdown,
    write_rtl_evidence,
)


class RtlEvidenceTests(unittest.TestCase):
    def test_parses_verilator_coverage_summary(self):
        summary = parse_verilator_coverage_summary(
            "Total coverage (898/1454) 61.00%\nSee lines with '%00' in annotated"
        )

        self.assertEqual(summary["covered_points"], 898)
        self.assertEqual(summary["total_points"], 1454)
        self.assertEqual(summary["percent"], 61.0)

    def test_complete_evidence_preserves_tool_and_run_provenance(self):
        coverage = RtlCoverageCollector()
        for identifier in list(coverage.points)[:33]:
            coverage.hit(identifier, "seed-11:tx-4:mem-read")

        evidence = build_rtl_evidence(
            coverage.report(scoreboard_comparisons=19, scoreboard_failures=[]),
            upstream_commit="cdc9ef7d4dfc3d8fbd969869f6696afe27cfed2a",
            tools={"picker": "1.2.3", "toffee": "0.2.1", "verilator": "5.020"},
            seeds=[11, 29, 73],
            transactions=384,
            waveform="artifacts/nutshell-cache-regression.fst",
            code_coverage={"status": "exported", "artifact": "artifacts/coverage.dat"},
        )

        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["status"], "rtl_functional_coverage_complete")
        self.assertEqual(evidence["run"]["seeds"], [11, 29, 73])
        self.assertEqual(evidence["run"]["transactions"], 384)
        self.assertEqual(evidence["coverage"]["covered"], 33)
        self.assertEqual(evidence["scoreboard"]["failures"], [])
        self.assertIn("picker", evidence["tools"])

    def test_markdown_distinguishes_functional_and_code_coverage(self):
        coverage = RtlCoverageCollector()
        evidence = build_rtl_evidence(
            coverage.report(0, []),
            upstream_commit="abc123",
            tools={},
            seeds=[11],
            transactions=0,
            waveform=None,
            code_coverage={"status": "not_exported", "reason": "没有可解析数据"},
        )

        markdown = render_rtl_markdown(evidence)

        self.assertIn("RTL 功能覆盖率", markdown)
        self.assertIn("RTL 代码覆盖率", markdown)
        self.assertIn("没有可解析数据", markdown)
        self.assertNotIn("Pending", markdown)

    def test_writer_emits_matching_json_and_markdown(self):
        coverage = RtlCoverageCollector()
        evidence = build_rtl_evidence(
            coverage.report(0, []), "abc123", {}, [11], 0, None, {"status": "not_exported"}
        )
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "rtl.json"
            markdown_path = Path(directory) / "rtl.md"
            write_rtl_evidence(evidence, json_path, markdown_path)

            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["status"], evidence["status"])
            self.assertIn("CacheSage-UC RTL 实测记录", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
