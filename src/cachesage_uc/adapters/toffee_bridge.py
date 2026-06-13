from __future__ import annotations

from typing import Dict, Iterable, List

from ..verification import Transaction


def to_toffee_case(transaction: Transaction) -> Dict[str, object]:
    line_base = transaction.address - (transaction.address % 16)
    return {
        "channel": "cache_req",
        "op": transaction.op,
        "addr": transaction.address,
        "data": transaction.data,
        "mask": transaction.mask,
        "meta": {
            "tag": transaction.tag,
            "line_base": line_base,
            "word_offset": (transaction.address - line_base) // 4,
            "byte_offset": transaction.address - line_base,
        },
    }


def to_toffee_cases(transactions: Iterable[Transaction]) -> List[Dict[str, object]]:
    return [to_toffee_case(transaction) for transaction in transactions]
