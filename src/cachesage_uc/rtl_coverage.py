from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


RTL_COVERPOINTS = {
    "rtl_read_miss_refill": "read miss causes a memory refill",
    "rtl_read_hit": "read hit returns without a memory refill",
    "rtl_write_miss_allocate": "write miss allocates a line",
    "rtl_write_hit": "write hit updates a resident line",
    "rtl_read_after_write": "read returns data from an earlier write",
    "rtl_full_mask_write": "full 8-byte mask write",
    "rtl_partial_mask_low": "partial write selects low bytes",
    "rtl_partial_mask_high": "partial write selects high bytes",
    "rtl_sparse_mask": "non-contiguous byte mask write",
    "rtl_line_first_word": "access first word of a cache line",
    "rtl_line_last_word": "access last word of a cache line",
    "rtl_adjacent_line": "access adjacent cache lines",
    "rtl_four_way_fill": "fill all four ways in one set",
    "rtl_same_set_replacement": "fifth line in one set triggers replacement",
    "rtl_victim_onehot": "victim way mask is one-hot",
    "rtl_victim_way_0": "replacement selects way 0",
    "rtl_victim_way_1": "replacement selects way 1",
    "rtl_victim_way_2": "replacement selects way 2",
    "rtl_victim_way_3": "replacement selects way 3",
    "rtl_clean_eviction": "clean victim is evicted without writeback",
    "rtl_dirty_eviction_writeback": "dirty victim produces writeback",
    "rtl_refill_after_writeback": "refill follows dirty writeback",
    "rtl_multi_set": "traffic reaches multiple set indices",
    "rtl_input_backpressure": "request waits for input ready",
    "rtl_memory_read_latency": "memory read response is delayed",
    "rtl_memory_write_latency": "memory write response is delayed",
    "rtl_response_backpressure": "response waits for consumer ready",
    "rtl_reset_recovery": "traffic passes after reset",
    "rtl_idle_empty": "pipeline returns to the observable empty state",
    "rtl_probe_miss": "coherence probe misses",
    "rtl_probe_hit_clean": "coherence probe hits a clean line",
    "rtl_probe_hit_dirty": "coherence probe hits a dirty line",
    "rtl_probe_data_return": "probe returns cached data",
    "rtl_probe_after_write": "probe follows a cache write",
    "rtl_probe_after_eviction": "probe observes an evicted line as missing",
    "rtl_probe_reaccess": "normal access after probe remains correct",
}


@dataclass
class CoverpointHit:
    identifier: str
    description: str
    hit_count: int = 0
    sources: List[str] = field(default_factory=list)

    def hit(self, source: str) -> None:
        self.hit_count += 1
        if source and source not in self.sources and len(self.sources) < 8:
            self.sources.append(source)

    def to_dict(self) -> dict:
        return {
            "id": self.identifier,
            "description": self.description,
            "hit_count": self.hit_count,
            "covered": self.hit_count > 0,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class RtlObservation:
    op: str
    address: int
    mask: int = 0xFF
    hit: Optional[bool] = None
    memory_read: bool = False
    memory_write: bool = False
    refill: bool = False
    victim_way: int = 0
    dirty_eviction: bool = False
    clean_eviction: bool = False
    writeback: bool = False
    read_after_write: bool = False
    same_set_depth: int = 0
    set_count: int = 1
    input_wait_cycles: int = 0
    memory_read_wait_cycles: int = 0
    memory_write_wait_cycles: int = 0
    response_wait_cycles: int = 0
    reset_recovered: bool = False
    idle_empty: bool = False
    probe_result: str = ""
    probe_data_returned: bool = False
    probe_after_write: bool = False
    probe_after_eviction: bool = False
    probe_reaccess: bool = False
    source: str = ""


@dataclass(frozen=True)
class RtlCoverageReport:
    status: str
    total: int
    covered: int
    percent: float
    coverpoints: List[dict]
    scoreboard_comparisons: int
    scoreboard_failures: List[dict]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "coverage": {"total": self.total, "covered": self.covered, "percent": self.percent},
            "coverpoints": list(self.coverpoints),
            "scoreboard": {
                "comparisons": self.scoreboard_comparisons,
                "failures": list(self.scoreboard_failures),
            },
        }


class RtlCoverageCollector:
    def __init__(self) -> None:
        self.points: Dict[str, CoverpointHit] = {
            identifier: CoverpointHit(identifier, description)
            for identifier, description in RTL_COVERPOINTS.items()
        }

    def hit(self, identifier: str, source: str = "") -> None:
        if identifier not in self.points:
            raise KeyError(f"unknown RTL coverpoint: {identifier}")
        self.points[identifier].hit(source)

    def observe(self, obs: RtlObservation) -> None:
        source = obs.source
        if obs.op == "read" and obs.hit is False and obs.memory_read and obs.refill:
            self.hit("rtl_read_miss_refill", source)
        if obs.op == "read" and obs.hit is True:
            self.hit("rtl_read_hit", source)
        if obs.op == "write" and obs.hit is False and obs.refill:
            self.hit("rtl_write_miss_allocate", source)
        if obs.op == "write" and obs.hit is True:
            self.hit("rtl_write_hit", source)
        if obs.read_after_write:
            self.hit("rtl_read_after_write", source)
        if obs.op == "write" and obs.mask == 0xFF:
            self.hit("rtl_full_mask_write", source)
        if obs.op == "write" and obs.mask != 0xFF and obs.mask & 0x0F:
            self.hit("rtl_partial_mask_low", source)
        if obs.op == "write" and obs.mask != 0xFF and obs.mask & 0xF0:
            self.hit("rtl_partial_mask_high", source)
        if obs.op == "write" and obs.mask not in {0, 0xFF, 0x0F, 0xF0}:
            self.hit("rtl_sparse_mask", source)
        offset = obs.address % 64
        if offset == 0:
            self.hit("rtl_line_first_word", source)
        if offset == 56:
            self.hit("rtl_line_last_word", source)
        if "adjacent-line" in source:
            self.hit("rtl_adjacent_line", source)
        if obs.same_set_depth >= 4:
            self.hit("rtl_four_way_fill", source)
        if obs.same_set_depth >= 5:
            self.hit("rtl_same_set_replacement", source)
        if obs.victim_way and obs.victim_way & (obs.victim_way - 1) == 0:
            self.hit("rtl_victim_onehot", source)
            way = obs.victim_way.bit_length() - 1
            if 0 <= way <= 3:
                self.hit(f"rtl_victim_way_{way}", source)
        if obs.clean_eviction:
            self.hit("rtl_clean_eviction", source)
        if obs.dirty_eviction and obs.writeback:
            self.hit("rtl_dirty_eviction_writeback", source)
        if obs.dirty_eviction and obs.writeback and obs.refill:
            self.hit("rtl_refill_after_writeback", source)
        if obs.set_count >= 2:
            self.hit("rtl_multi_set", source)
        if obs.input_wait_cycles:
            self.hit("rtl_input_backpressure", source)
        if obs.memory_read_wait_cycles:
            self.hit("rtl_memory_read_latency", source)
        if obs.memory_write_wait_cycles:
            self.hit("rtl_memory_write_latency", source)
        if obs.response_wait_cycles:
            self.hit("rtl_response_backpressure", source)
        if obs.reset_recovered:
            self.hit("rtl_reset_recovery", source)
        if obs.idle_empty:
            self.hit("rtl_idle_empty", source)
        probe_map = {
            "miss": "rtl_probe_miss",
            "clean_hit": "rtl_probe_hit_clean",
            "dirty_hit": "rtl_probe_hit_dirty",
        }
        if obs.probe_result in probe_map:
            self.hit(probe_map[obs.probe_result], source)
        if obs.probe_data_returned:
            self.hit("rtl_probe_data_return", source)
        if obs.probe_after_write:
            self.hit("rtl_probe_after_write", source)
        if obs.probe_after_eviction:
            self.hit("rtl_probe_after_eviction", source)
        if obs.probe_reaccess:
            self.hit("rtl_probe_reaccess", source)

    def report(self, scoreboard_comparisons: int, scoreboard_failures: List[dict]) -> RtlCoverageReport:
        covered = sum(point.hit_count > 0 for point in self.points.values())
        total = len(self.points)
        percent = round(covered * 100.0 / total, 2)
        if scoreboard_failures:
            status = "rtl_functional_coverage_failed"
        elif covered >= 33:
            status = "rtl_functional_coverage_complete"
        else:
            status = "rtl_functional_coverage_below_threshold"
        return RtlCoverageReport(
            status=status,
            total=total,
            covered=covered,
            percent=percent,
            coverpoints=[point.to_dict() for point in self.points.values()],
            scoreboard_comparisons=scoreboard_comparisons,
            scoreboard_failures=list(scoreboard_failures),
        )
