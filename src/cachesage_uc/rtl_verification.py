from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional


RTL_WORD_BYTES = 8
RTL_DATA_MASK = (1 << 64) - 1
RTL_BYTE_MASK = (1 << RTL_WORD_BYTES) - 1


@dataclass(frozen=True)
class RtlCacheConfig:
    line_size: int = 64
    sets: int = 128
    ways: int = 4

    @property
    def same_set_stride(self) -> int:
        return self.line_size * self.sets

    def line_base(self, address: int) -> int:
        return address - (address % self.line_size)

    def set_index(self, address: int) -> int:
        return (self.line_base(address) // self.line_size) % self.sets


RTL_CACHE_CONFIG = RtlCacheConfig()


@dataclass(frozen=True)
class RtlTransaction:
    op: str
    address: int
    data: int = 0
    mask: int = RTL_BYTE_MASK
    size: int = 7
    tag: str = ""

    def __post_init__(self) -> None:
        if self.op not in {"read", "write", "probe"}:
            raise ValueError(f"unsupported RTL transaction op: {self.op}")
        if self.address < 0 or self.address % RTL_WORD_BYTES:
            raise ValueError("RTL transaction address must be non-negative and 8-byte aligned")
        if not 0 <= self.data <= RTL_DATA_MASK:
            raise ValueError("RTL transaction data must fit in 64 bits")
        if not 0 <= self.mask <= RTL_BYTE_MASK:
            raise ValueError("RTL transaction mask must fit in 8 bits")

    @classmethod
    def read(cls, address: int, tag: str = "") -> "RtlTransaction":
        return cls(op="read", address=address, tag=tag)

    @classmethod
    def write(cls, address: int, data: int, mask: int = RTL_BYTE_MASK, tag: str = "") -> "RtlTransaction":
        return cls(op="write", address=address, data=data, mask=mask, tag=tag)

    @classmethod
    def probe(cls, address: int, tag: str = "") -> "RtlTransaction":
        return cls(op="probe", address=address, tag=tag)

    def to_dict(self) -> dict:
        return {
            "op": self.op,
            "address": self.address,
            "data": self.data,
            "mask": self.mask,
            "size": self.size,
            "tag": self.tag,
        }


class RtlReferenceMemory:
    def __init__(self) -> None:
        self._bytes: Dict[int, int] = {}

    def read(self, address: int) -> int:
        return sum((self._bytes.get(address + offset, 0) & 0xFF) << (8 * offset) for offset in range(RTL_WORD_BYTES))

    def apply(self, transaction: RtlTransaction) -> Optional[int]:
        if transaction.op == "read":
            return self.read(transaction.address)
        if transaction.op == "write":
            for offset in range(RTL_WORD_BYTES):
                if transaction.mask & (1 << offset):
                    self._bytes[transaction.address + offset] = (transaction.data >> (8 * offset)) & 0xFF
            return None
        return None


class RtlScoreboard:
    def __init__(self) -> None:
        self.reference = RtlReferenceMemory()
        self.comparisons = 0
        self.failures: List[dict] = []

    def observe(
        self,
        transaction: RtlTransaction,
        observed_data: Optional[int],
        seed: int,
        index: int,
    ) -> None:
        expected = self.reference.apply(transaction)
        if transaction.op != "read":
            return
        self.comparisons += 1
        observed = 0 if observed_data is None else int(observed_data) & RTL_DATA_MASK
        if expected != observed:
            self.failures.append(
                {
                    "seed": seed,
                    "index": index,
                    "tag": transaction.tag,
                    "transaction": transaction.to_dict(),
                    "expected": expected,
                    "observed": observed,
                    "message": (
                        f"read mismatch at 0x{transaction.address:08X}: "
                        f"expected 0x{expected:016X}, observed 0x{observed:016X}"
                    ),
                }
            )


def build_rtl_directed_sequence() -> List[RtlTransaction]:
    stride = RTL_CACHE_CONFIG.same_set_stride
    sequence = [
        RtlTransaction.read(0x0000, "read-miss-refill"),
        RtlTransaction.read(0x0000, "read-hit"),
        RtlTransaction.write(0x0000, 0x1122334455667788, tag="write-hit-full"),
        RtlTransaction.write(0x0008, 0xFFEEDDCCBBAA0099, mask=0x0F, tag="mask-low"),
        RtlTransaction.write(0x0010, 0x0123456789ABCDEF, mask=0xF0, tag="mask-high"),
        RtlTransaction.write(0x0018, 0xA5A5A5A55A5A5A5A, mask=0x55, tag="mask-sparse"),
        RtlTransaction.read(0x0000, "read-after-write"),
        RtlTransaction.read(0x0038, "line-last-word"),
        RtlTransaction.read(0x0040, "adjacent-line"),
        RtlTransaction.read(0x0080, "multi-set"),
    ]
    for way in range(RTL_CACHE_CONFIG.ways + 2):
        sequence.append(RtlTransaction.write(way * stride, 0x1000 + way, tag=f"same-set-{way}"))
    sequence.extend(
        [
            RtlTransaction.probe(0x6000, "probe-miss"),
            RtlTransaction.probe(0x0000, "probe-after-write"),
        ]
    )
    return sequence


def build_rtl_random_sequence(seed: int, count: int) -> List[RtlTransaction]:
    if count < 0:
        raise ValueError("count must be non-negative")
    rng = random.Random(seed)
    sequence: List[RtlTransaction] = []
    masks = [0xFF, 0x0F, 0xF0, 0x55, 0x33]
    for index in range(count):
        set_index = rng.randrange(0, 16)
        tag = rng.randrange(0, 8)
        word = rng.randrange(0, RTL_CACHE_CONFIG.line_size // RTL_WORD_BYTES)
        address = tag * RTL_CACHE_CONFIG.same_set_stride + set_index * RTL_CACHE_CONFIG.line_size + word * RTL_WORD_BYTES
        if rng.random() < 0.55:
            sequence.append(
                RtlTransaction.write(
                    address,
                    rng.randrange(0, RTL_DATA_MASK + 1),
                    mask=rng.choice(masks),
                    tag=f"seed-{seed}-write-{index}",
                )
            )
        else:
            sequence.append(RtlTransaction.read(address, tag=f"seed-{seed}-read-{index}"))
    return sequence
