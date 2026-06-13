from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


WORD_BYTES = 4


class FaultMode(str, Enum):
    NONE = "none"
    DROP_DIRTY_WRITEBACK = "drop_dirty_writeback"
    IGNORE_WRITE_MASK = "ignore_write_mask"
    STUCK_REPLACEMENT = "stuck_replacement"


@dataclass(frozen=True)
class CacheConfig:
    line_size: int = 16
    sets: int = 2
    ways: int = 2

    def __post_init__(self) -> None:
        if self.line_size % WORD_BYTES != 0:
            raise ValueError("line_size must be word-aligned")
        if self.sets <= 0 or self.ways <= 0:
            raise ValueError("sets and ways must be positive")


@dataclass(frozen=True)
class Transaction:
    op: str
    address: int
    data: int = 0
    mask: int = 0b1111
    tag: str = ""

    @classmethod
    def read(cls, address: int, tag: str = "") -> "Transaction":
        return cls(op="read", address=address, tag=tag)

    @classmethod
    def write(cls, address: int, data: int, mask: int = 0b1111, tag: str = "") -> "Transaction":
        return cls(op="write", address=address, data=data & 0xFFFFFFFF, mask=mask & 0b1111, tag=tag)

    def to_dict(self) -> Dict[str, object]:
        return {
            "op": self.op,
            "address": self.address,
            "data": self.data,
            "mask": self.mask,
            "tag": self.tag,
        }


@dataclass(frozen=True)
class CacheEvent:
    kind: str
    address: int
    detail: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {"kind": self.kind, "address": self.address, "detail": self.detail}


@dataclass(frozen=True)
class TransactionResult:
    transaction: Transaction
    data: Optional[int]
    events: List[CacheEvent]

    def to_dict(self) -> Dict[str, object]:
        return {
            "transaction": self.transaction.to_dict(),
            "data": self.data,
            "events": [event.to_dict() for event in self.events],
        }


@dataclass
class CacheLine:
    valid: bool = False
    dirty: bool = False
    tag: int = 0
    base_address: int = 0
    data: bytearray = field(default_factory=bytearray)


class CacheModel:
    def __init__(self, config: CacheConfig, fault: FaultMode = FaultMode.NONE):
        self.config = config
        self.fault = FaultMode(fault)
        self.memory: Dict[int, int] = {}
        self.events: List[CacheEvent] = []
        self._sets: List[List[CacheLine]] = [
            [CacheLine(data=bytearray(config.line_size)) for _ in range(config.ways)]
            for _ in range(config.sets)
        ]
        self._next_victim = [0 for _ in range(config.sets)]

    def read_memory_word(self, address: int) -> int:
        return _bytes_to_word([self.memory.get(address + i, 0) for i in range(WORD_BYTES)])

    def write_memory_word(self, address: int, value: int) -> None:
        for offset, byte in enumerate(_word_to_bytes(value)):
            self.memory[address + offset] = byte

    def apply(self, transaction: Transaction) -> TransactionResult:
        line, local_events = self._get_line(transaction.address)
        offset = transaction.address - line.base_address
        if offset < 0 or offset + WORD_BYTES > self.config.line_size:
            raise ValueError("transaction crosses a cache-line boundary")

        data: Optional[int]
        if transaction.op == "read":
            data = _bytes_to_word(line.data[offset : offset + WORD_BYTES])
            local_events.append(CacheEvent("read", transaction.address, transaction.tag))
        elif transaction.op == "write":
            mask = 0b1111 if self.fault == FaultMode.IGNORE_WRITE_MASK else transaction.mask
            incoming = _word_to_bytes(transaction.data)
            for byte_index in range(WORD_BYTES):
                if mask & (1 << byte_index):
                    line.data[offset + byte_index] = incoming[byte_index]
            line.dirty = True
            data = None
            local_events.append(CacheEvent("write", transaction.address, transaction.tag))
            if transaction.mask != 0b1111:
                local_events.append(CacheEvent("masked_write", transaction.address, f"mask={transaction.mask:04b}"))
        else:
            raise ValueError(f"unknown transaction op: {transaction.op}")

        self.events.extend(local_events)
        return TransactionResult(transaction=transaction, data=data, events=local_events)

    def _get_line(self, address: int) -> Tuple[CacheLine, List[CacheEvent]]:
        base_address = self._line_base(address)
        set_index = self._set_index(base_address)
        tag = self._tag(base_address)
        events: List[CacheEvent] = []

        for line in self._sets[set_index]:
            if line.valid and line.tag == tag:
                events.append(CacheEvent("hit", base_address))
                return line, events

        events.append(CacheEvent("miss", base_address))
        victim = self._choose_victim(set_index)
        if victim.valid:
            events.append(CacheEvent("eviction", victim.base_address, "dirty" if victim.dirty else "clean"))
            if victim.dirty:
                events.append(CacheEvent("dirty_eviction", victim.base_address))
                if self.fault != FaultMode.DROP_DIRTY_WRITEBACK:
                    self._writeback(victim)
                    events.append(CacheEvent("writeback", victim.base_address))

        victim.valid = True
        victim.dirty = False
        victim.tag = tag
        victim.base_address = base_address
        victim.data = bytearray(self.memory.get(base_address + i, 0) for i in range(self.config.line_size))
        events.append(CacheEvent("refill", base_address))
        return victim, events

    def _choose_victim(self, set_index: int) -> CacheLine:
        for line in self._sets[set_index]:
            if not line.valid:
                return line

        victim_index = self._next_victim[set_index]
        victim = self._sets[set_index][victim_index]
        if self.fault != FaultMode.STUCK_REPLACEMENT:
            self._next_victim[set_index] = (victim_index + 1) % self.config.ways
        return victim

    def _writeback(self, line: CacheLine) -> None:
        for offset, byte in enumerate(line.data):
            self.memory[line.base_address + offset] = byte

    def _line_base(self, address: int) -> int:
        return address - (address % self.config.line_size)

    def _set_index(self, base_address: int) -> int:
        return (base_address // self.config.line_size) % self.config.sets

    def _tag(self, base_address: int) -> int:
        return (base_address // self.config.line_size) // self.config.sets


@dataclass(frozen=True)
class ScoreboardFailure:
    index: int
    tag: str
    message: str

    def to_dict(self) -> Dict[str, object]:
        return {"index": self.index, "tag": self.tag, "message": self.message}


@dataclass(frozen=True)
class CoverageResult:
    total: int
    covered: int
    percent: float

    def to_dict(self) -> Dict[str, object]:
        return {"total": self.total, "covered": self.covered, "percent": self.percent}


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    seed: Optional[int]
    transaction_count: int
    covered_points: List[str]
    coverage: CoverageResult
    failures: List[ScoreboardFailure]
    event_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "passed": self.passed,
            "seed": self.seed,
            "transaction_count": self.transaction_count,
            "covered_points": list(self.covered_points),
            "coverage": self.coverage.to_dict(),
            "failures": [failure.to_dict() for failure in self.failures],
            "event_counts": dict(self.event_counts),
        }


class VerificationRunner:
    def __init__(self, config: CacheConfig = CacheConfig()):
        self.config = config

    def run(
        self,
        transactions: Sequence[Transaction],
        fault: FaultMode = FaultMode.NONE,
        seed: Optional[int] = None,
    ) -> VerificationResult:
        reference = CacheModel(self.config)
        candidate = CacheModel(self.config, fault=fault)
        data_failures: List[ScoreboardFailure] = []
        memory_failures: List[ScoreboardFailure] = []

        for index, transaction in enumerate(transactions):
            expected = reference.apply(transaction)
            observed = candidate.apply(transaction)
            if expected.data != observed.data:
                data_failures.append(
                    ScoreboardFailure(
                        index=index,
                        tag=transaction.tag,
                        message=(
                            f"data mismatch at 0x{transaction.address:X}: "
                            f"expected {expected.data!r}, observed {observed.data!r}"
                        ),
                    )
                )

        for address in _observed_word_addresses(transactions):
            expected_word = reference.read_memory_word(address)
            observed_word = candidate.read_memory_word(address)
            if expected_word != observed_word:
                memory_failures.append(
                    ScoreboardFailure(
                        index=len(transactions),
                        tag="final-memory",
                        message=(
                            f"memory mismatch at 0x{address:X}: "
                            f"expected 0x{expected_word:08X}, observed 0x{observed_word:08X}"
                        ),
                    )
                )
                break

        failures = memory_failures + data_failures
        covered = _derive_coverage(transactions, candidate.events)
        event_counts = _count_events(candidate.events)
        coverage = CoverageResult(
            total=len(ALL_COVERPOINTS),
            covered=len(covered),
            percent=round(len(covered) * 100.0 / len(ALL_COVERPOINTS), 2),
        )
        return VerificationResult(
            passed=not failures,
            seed=seed,
            transaction_count=len(transactions),
            covered_points=sorted(covered),
            coverage=coverage,
            failures=failures,
            event_counts=event_counts,
        )


ALL_COVERPOINTS = {
    "cp_read_hit",
    "cp_write_hit_mask",
    "cp_read_miss_refill",
    "cp_write_miss_allocate",
    "cp_dirty_eviction",
    "cp_clean_eviction",
    "cp_replacement_rotation",
    "cp_refill_alignment",
    "cp_stall_hold",
    "cp_reset_recovery",
    "cp_boundary_address",
    "cp_long_random",
}


def build_directed_eviction_sequence() -> List[Transaction]:
    return [
        Transaction.write(0x00, 0xDEADBEEF, tag="dirty-victim"),
        Transaction.read(0x20, tag="same-set-fill-a"),
        Transaction.read(0x40, tag="same-set-fill-b"),
        Transaction.read(0x00, tag="victim-readback"),
    ]


def build_seeded_random_sequence(seed: int, count: int) -> List[Transaction]:
    rng = random.Random(seed)
    sequence = [
        Transaction.write(0x00, 0x01020304, tag="warm-line"),
        Transaction.write(0x00, 0xAABBCCDD, mask=0b0011, tag="masked-hit"),
        Transaction.read(0x10, tag="cold-read"),
        Transaction.write(0x20, 0x55667788, tag="same-set-write"),
        Transaction.read(0x40, tag="same-set-evict"),
        Transaction.read(0x00, tag="dirty-readback"),
    ]
    while len(sequence) < count:
        line = rng.randrange(0, 12)
        address = line * 0x10
        if rng.random() < 0.55:
            mask = rng.choice([0b1111, 0b0011, 0b1100, 0b0101])
            data = rng.randrange(0, 0xFFFFFFFF)
            sequence.append(Transaction.write(address, data, mask=mask, tag=f"rand-w{len(sequence)}"))
        else:
            sequence.append(Transaction.read(address, tag=f"rand-r{len(sequence)}"))
    return sequence[:count]


def _derive_coverage(transactions: Sequence[Transaction], events: Sequence[CacheEvent]) -> Set[str]:
    covered: Set[str] = set()
    event_kinds = [event.kind for event in events]
    event_details = [event.detail for event in events]
    addresses = [transaction.address for transaction in transactions]

    if "hit" in event_kinds and any(transaction.op == "read" for transaction in transactions):
        covered.add("cp_read_hit")
    if any(transaction.op == "write" and transaction.mask != 0b1111 for transaction in transactions):
        covered.add("cp_write_hit_mask")
    if "miss" in event_kinds and "refill" in event_kinds and any(transaction.op == "read" for transaction in transactions):
        covered.add("cp_read_miss_refill")
        covered.add("cp_refill_alignment")
    if any(transaction.op == "write" for transaction in transactions) and "miss" in event_kinds:
        covered.add("cp_write_miss_allocate")
    if "dirty_eviction" in event_kinds:
        covered.add("cp_dirty_eviction")
    if "clean" in event_details:
        covered.add("cp_clean_eviction")
    if "eviction" in event_kinds:
        covered.add("cp_replacement_rotation")
    if len(transactions) >= 32:
        covered.add("cp_long_random")
    if _has_neighboring_lines(addresses):
        covered.add("cp_boundary_address")
    return covered


def _observed_word_addresses(transactions: Sequence[Transaction]) -> List[int]:
    return sorted({transaction.address - (transaction.address % WORD_BYTES) for transaction in transactions})


def _count_events(events: Iterable[CacheEvent]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        counts[event.kind] = counts.get(event.kind, 0) + 1
    return counts


def _has_neighboring_lines(addresses: Sequence[int]) -> bool:
    bases = sorted({address - (address % 16) for address in addresses})
    return any(right - left == 16 for left, right in zip(bases, bases[1:]))


def _word_to_bytes(value: int) -> List[int]:
    return [(value >> (8 * i)) & 0xFF for i in range(WORD_BYTES)]


def _bytes_to_word(data: Sequence[int]) -> int:
    value = 0
    for index, byte in enumerate(data[:WORD_BYTES]):
        value |= (int(byte) & 0xFF) << (8 * index)
    return value
