from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class CoveragePoint:
    identifier: str
    description: str
    covered: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "description": self.description,
            "covered": self.covered,
        }


@dataclass(frozen=True)
class Scenario:
    identifier: str
    name: str
    intent: str
    method: str
    coverage_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "intent": self.intent,
            "method": self.method,
            "coverage_points": list(self.coverage_points),
        }


@dataclass(frozen=True)
class Intervention:
    stage: str
    ai_output: str
    human_action: str
    lesson: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "stage": self.stage,
            "ai_output": self.ai_output,
            "human_action": self.human_action,
            "lesson": self.lesson,
        }


@dataclass(frozen=True)
class CoverageSummary:
    total: int
    covered: int
    percent: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "total": self.total,
            "covered": self.covered,
            "percent": self.percent,
        }


@dataclass(frozen=True)
class VerificationPlan:
    title: str
    dut: str
    scenarios: List[Scenario]
    coverage_points: List[CoveragePoint]

    def to_dict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "dut": self.dut,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "coverage_points": [point.to_dict() for point in self.coverage_points],
        }


@dataclass(frozen=True)
class EvidenceBundle:
    plan: VerificationPlan
    interventions: List[Intervention]
    fault_injection: List[str] = field(default_factory=list)

    def coverage_summary(self) -> CoverageSummary:
        total = len(self.plan.coverage_points)
        covered = sum(1 for point in self.plan.coverage_points if point.covered)
        percent = 0.0 if total == 0 else round(covered * 100.0 / total, 2)
        return CoverageSummary(total=total, covered=covered, percent=percent)

    def to_dict(self) -> Dict[str, object]:
        return {
            **self.plan.to_dict(),
            "coverage_summary": self.coverage_summary().to_dict(),
            "interventions": [item.to_dict() for item in self.interventions],
            "fault_injection": list(self.fault_injection),
        }


def build_default_bundle() -> EvidenceBundle:
    coverage_points = [
        CoveragePoint("cp_read_hit", "Read hit returns stable data without refill"),
        CoveragePoint("cp_write_hit_mask", "Masked write hit updates only selected bytes"),
        CoveragePoint("cp_read_miss_refill", "Read miss requests refill and replays load"),
        CoveragePoint("cp_write_miss_allocate", "Write miss allocates line and preserves mask semantics"),
        CoveragePoint("cp_dirty_eviction", "Dirty eviction writes back victim before replacement"),
        CoveragePoint("cp_clean_eviction", "Clean eviction does not emit writeback"),
        CoveragePoint("cp_replacement_rotation", "Replacement state advances under conflict pressure"),
        CoveragePoint("cp_refill_alignment", "Refill beats land in the expected line offsets"),
        CoveragePoint("cp_stall_hold", "Stall and back-pressure keep request metadata stable"),
        CoveragePoint("cp_reset_recovery", "Reset clears transient state before new traffic"),
        CoveragePoint("cp_boundary_address", "Boundary addresses do not alias adjacent cache lines"),
        CoveragePoint("cp_long_random", "Long random stream agrees with the reference memory model"),
    ]
    scenarios = [
        Scenario(
            "S01",
            "Read/write smoke path",
            "Prove the Python driver, monitor, and scoreboard can close a simple cache transaction loop.",
            "Directed loads and stores to one cache line, checked against the reference memory model.",
            ["cp_read_hit", "cp_write_hit_mask"],
        ),
        Scenario(
            "S02",
            "Read miss and refill",
            "Exercise miss request, refill acceptance, and replayed response ordering.",
            "Cold read sequence with deterministic downstream memory latency.",
            ["cp_read_miss_refill", "cp_refill_alignment"],
        ),
        Scenario(
            "S03",
            "Write miss allocate",
            "Check write-allocate behavior and byte mask preservation after a miss.",
            "Masked stores to cold lines followed by reads that expose unintended byte corruption.",
            ["cp_write_miss_allocate", "cp_write_hit_mask"],
        ),
        Scenario(
            "S04",
            "Dirty eviction integrity",
            "Catch victim writeback loss before a replacement installs the new line.",
            "Fill a set, dirty the victim, force replacement, then read the evicted address through memory.",
            ["cp_dirty_eviction", "cp_replacement_rotation"],
        ),
        Scenario(
            "S05",
            "Clean eviction silence",
            "Make sure clean victims do not create phantom writebacks.",
            "Conflict stream with monitor assertions on writeback channel quietness.",
            ["cp_clean_eviction", "cp_replacement_rotation"],
        ),
        Scenario(
            "S06",
            "Replacement stress",
            "Stress set conflicts until replacement policy state errors become visible.",
            "Constrained random addresses pinned to the same set, with seed replay for failures.",
            ["cp_replacement_rotation", "cp_long_random"],
        ),
        Scenario(
            "S07",
            "Stall and back-pressure",
            "Verify metadata is held stable while request, refill, or response channels stall.",
            "Random stall injection on each handshake boundary plus scoreboard event ordering checks.",
            ["cp_stall_hold", "cp_refill_alignment"],
        ),
        Scenario(
            "S08",
            "Reset recovery",
            "Check that reset cancels transient cache activity before the next legal request.",
            "Reset pulses during miss/refill windows followed by a clean smoke sequence.",
            ["cp_reset_recovery", "cp_read_miss_refill"],
        ),
        Scenario(
            "S09",
            "Boundary address aliasing",
            "Defend against line-offset and tag slicing mistakes at boundary addresses.",
            "Neighboring line accesses with alternating masks and post-check reads.",
            ["cp_boundary_address", "cp_write_hit_mask"],
        ),
        Scenario(
            "S10",
            "Long random regression",
            "Let coverage holes and scoreboard mismatches drive the next UCAgent prompt round.",
            "Seeded CRV stream with address distribution, read/write ratio, and stall knobs.",
            ["cp_long_random", "cp_dirty_eviction", "cp_stall_hold"],
        ),
    ]
    interventions = [
        Intervention(
            "Test-plan drafting",
            "The first AI plan listed read/write hits and misses but treated replacement as a single generic case.",
            "Split replacement into clean eviction, dirty eviction, and same-set pressure scenarios.",
            "Coverage should name the cache invariant being protected, not just the operation category.",
        ),
        Intervention(
            "Scoreboard design",
            "The generated checker compared only final read data and ignored writeback ordering.",
            "Added a scoreboard obligation for victim writeback before refill installation.",
            "Cache correctness depends on event order as much as end-state memory contents.",
        ),
        Intervention(
            "CRV constraints",
            "The AI suggested uniform random addresses, which rarely hits replacement pressure quickly.",
            "Biased address generation toward one set, then kept a smaller percentage of full-range traffic.",
            "Good coverage comes from shaped randomness plus a few directed invariants.",
        ),
        Intervention(
            "Failure triage",
            "The draft prompt asked the agent to fix any mismatch from the waveform summary directly.",
            "Changed the flow so the human first classifies scoreboard bug, DUT bug, or stimulus bug.",
            "Prompt tuning is useful after the failure has a credible engineering diagnosis.",
        ),
        Intervention(
            "Report hygiene",
            "The AI-generated report phrased planned coverage as completed coverage.",
            "Reworded the initial report to separate planned coverpoints from RTL-measured results.",
            "Competition reports should be ambitious, but the evidence must stay audit-friendly.",
        ),
    ]
    faults = [
        "Replacement state does not advance after a refill",
        "Dirty bit is cleared before victim writeback is accepted",
        "Refill beat index is shifted by one word",
        "Write mask is ignored on store hit",
        "Request metadata changes while downstream ready is low",
    ]
    return EvidenceBundle(
        plan=VerificationPlan(
            title="CacheSage-UC NutShell Cache Verification Plan",
            dut="NutShell Cache",
            scenarios=scenarios,
            coverage_points=coverage_points,
        ),
        interventions=interventions,
        fault_injection=faults,
    )


def render_markdown_report(bundle: EvidenceBundle) -> str:
    summary = bundle.coverage_summary()
    lines = [
        "# CacheSage-UC Initial Verification Report",
        "",
        "This report is the initial evidence package for the UCAgent NutShell Cache track. "
        "It records the verification intent, coverage model, AI-human review trail, and "
        "fault-injection targets before the RTL regression is attached.",
        "",
        "## Verification Scope",
        "",
        f"- DUT: {bundle.plan.dut}",
        f"- Scenarios: {len(bundle.plan.scenarios)}",
        f"- Coverage points tracked: {summary.covered}/{summary.total} ({summary.percent:.2f}%)",
        "- Current status: plan and evidence tooling are ready; RTL-measured coverage is reported separately once Picker/Toffee runs are wired in.",
        "",
        "## Scenario Matrix",
        "",
        "| ID | Scenario | Intent | Coverage |",
        "| --- | --- | --- | --- |",
    ]
    for scenario in bundle.plan.scenarios:
        coverage = ", ".join(scenario.coverage_points)
        lines.append(f"| {scenario.identifier} | {scenario.name} | {scenario.intent} | {coverage} |")

    lines.extend(
        [
            "",
            "## AI 缺陷与人工修正对比表",
            "",
            "| Stage | AI output | Human correction | Lesson |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in bundle.interventions:
        lines.append(
            f"| {item.stage} | {item.ai_output} | {item.human_action} | {item.lesson} |"
        )

    lines.extend(
        [
            "",
            "## 故障注入",
            "",
        ]
    )
    for fault in bundle.fault_injection:
        lines.append(f"- {fault}")

    lines.extend(
        [
            "",
            "## Next Regression Gate",
            "",
            "The next gate is to connect these scenarios to the Picker-generated Python DUT, "
            "run the Toffee environment with deterministic seeds, and replace planned coverage "
            "with measured functional coverage plus failure artifacts.",
            "",
        ]
    )
    return "\n".join(lines)
