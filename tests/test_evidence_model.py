from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


class EvidenceModelTests(unittest.TestCase):
    def test_default_plan_covers_cache_paths_that_matter(self):
        from cachesage_uc.evidence import build_default_bundle

        bundle = build_default_bundle()
        scenario_text = "\n".join(
            f"{scenario.name} {scenario.intent} {scenario.method}"
            for scenario in bundle.plan.scenarios
        ).lower()

        self.assertGreaterEqual(len(bundle.plan.scenarios), 10)
        self.assertGreaterEqual(len(bundle.plan.coverage_points), 20)
        self.assertIn("dirty eviction", scenario_text)
        self.assertIn("replacement", scenario_text)
        self.assertIn("refill", scenario_text)
        self.assertIn("stall", scenario_text)

        for scenario in bundle.plan.scenarios:
            self.assertTrue(scenario.identifier.startswith("S"))
            self.assertTrue(scenario.intent)
            self.assertTrue(scenario.method)
            self.assertTrue(scenario.coverage_points)

    def test_coverage_summary_is_computed_from_real_points(self):
        from cachesage_uc.evidence import CoveragePoint, EvidenceBundle, VerificationPlan

        plan = VerificationPlan(
            title="unit plan",
            dut="NutShell Cache",
            scenarios=[],
            coverage_points=[
                CoveragePoint("read_hit", "read hit", True),
                CoveragePoint("write_miss", "write miss", True),
                CoveragePoint("dirty_replace", "dirty replacement", False),
            ],
        )
        summary = EvidenceBundle(plan=plan, interventions=[]).coverage_summary()

        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.covered, 2)
        self.assertEqual(summary.percent, 66.67)

    def test_ai_human_intervention_log_has_actionable_human_corrections(self):
        from cachesage_uc.evidence import build_default_bundle

        bundle = build_default_bundle()

        self.assertGreaterEqual(len(bundle.interventions), 4)
        self.assertTrue(any("scoreboard" in item.human_action.lower() for item in bundle.interventions))
        self.assertTrue(any("coverage" in item.lesson.lower() for item in bundle.interventions))
        self.assertTrue(all(item.ai_output and item.human_action and item.lesson for item in bundle.interventions))

    def test_markdown_report_contains_competition_evidence_without_placeholders(self):
        from cachesage_uc.evidence import build_default_bundle, render_markdown_report

        report = render_markdown_report(build_default_bundle())

        self.assertIn("# CacheSage-UC Verification Evidence Report", report)
        self.assertIn("AI 盲区与人工修正对比表", report)
        self.assertIn("dirty eviction", report.lower())
        self.assertIn("故障注入", report)
        self.assertIn("Python harness measured coverage", report)
        self.assertIn("RTL/Toffee measured coverage", report)
        self.assertNotIn("缂?", report)
        self.assertNotIn("閺?", report)
        self.assertNotIn("TODO", report)
        self.assertNotIn("TBD", report)


if __name__ == "__main__":
    unittest.main()
