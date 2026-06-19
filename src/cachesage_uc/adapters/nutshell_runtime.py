from __future__ import annotations

from typing import Any, Dict

from ..rtl_verification import RtlTransaction


class NutShellRequestDriver:
    """Drive SimpleBus with explicit field ordering.

    The upstream convenience queue constructs request objects positionally. This
    adapter keeps size, byte mask and 64-bit data distinct at the protocol edge.
    """

    def __init__(self, agent: Any, read_cmd: int, write_cmd: int) -> None:
        self.agent = agent
        self.read_cmd = read_cmd
        self.write_cmd = write_cmd

    async def execute(self, transaction: RtlTransaction) -> Dict[str, int]:
        if transaction.op == "probe":
            raise ValueError("probe traffic requires the coherence driver")
        command = self.read_cmd if transaction.op == "read" else self.write_cmd
        await self.agent.send_req(
            transaction.address,
            transaction.size,
            command,
            transaction.mask if transaction.op == "write" else 0,
            transaction.data if transaction.op == "write" else 0,
        )
        return await self.agent.get_resp()
