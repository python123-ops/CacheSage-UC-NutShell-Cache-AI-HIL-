from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from ..rtl_verification import RtlTransaction


@dataclass(frozen=True)
class BackpressureTrace:
    input_wait_cycles: int
    response_wait_cycles: int
    request_payload_stable: bool
    response_payload_stable: bool
    ordered_responses: bool
    responses: List[Dict[str, int]]

    def to_dict(self) -> dict:
        return {
            "input_wait_cycles": self.input_wait_cycles,
            "response_wait_cycles": self.response_wait_cycles,
            "request_payload_stable": self.request_payload_stable,
            "response_payload_stable": self.response_payload_stable,
            "ordered_responses": self.ordered_responses,
            "response_count": len(self.responses),
        }


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

    def _request_payload(self, transaction: RtlTransaction) -> Dict[str, int]:
        command = self.read_cmd if transaction.op == "read" else self.write_cmd
        return {
            "addr": transaction.address,
            "size": transaction.size,
            "cmd": command,
            "wmask": transaction.mask if transaction.op == "write" else 0,
            "wdata": transaction.data if transaction.op == "write" else 0,
        }

    @staticmethod
    def _sample(channel: Any, fields: Sequence[str]) -> Dict[str, int]:
        return {name: int(getattr(channel, name).value) for name in fields}

    async def execute_backpressure_burst(
        self,
        transactions: Sequence[RtlTransaction],
        minimum_response_wait_cycles: int = 3,
        timeout_cycles: int = 512,
    ) -> BackpressureTrace:
        """Fill the request path while response ready is low, then drain in order.

        A request remains asserted until its ready/valid handshake completes. The
        first response is held for ``minimum_response_wait_cycles`` and is only
        released after the DUT has also deasserted request ready. This makes both
        coverpoints originate from observed DUT handshakes rather than labels.
        """

        if len(transactions) < 2:
            raise ValueError("backpressure burst requires at least two transactions")
        if minimum_response_wait_cycles < 1:
            raise ValueError("minimum_response_wait_cycles must be positive")
        if timeout_cycles < 1:
            raise ValueError("timeout_cycles must be positive")
        if any(transaction.op == "probe" for transaction in transactions):
            raise ValueError("probe traffic requires the coherence driver")

        bundle = self.agent.bundle
        set_immediate = getattr(bundle, "set_write_mode_as_imme", None)
        if set_immediate is not None:
            set_immediate()
        responses: List[Dict[str, int]] = []
        input_wait_cycles = 0
        response_wait_cycles = 0
        request_payload_stable = True
        response_payload_stable = True

        async def wait_high(signal: Any, purpose: str) -> None:
            for _ in range(timeout_cycles):
                if bool(signal.value):
                    return
                event = getattr(signal, "event", None)
                if event is None:
                    await bundle.step()
                else:
                    await event.wait()
            raise TimeoutError(f"backpressure burst timed out waiting for {purpose}")

        async def send_request(transaction: RtlTransaction) -> None:
            payload = self._request_payload(transaction)
            await wait_high(bundle.req.ready, "request ready")
            bundle.req.assign({"valid": 1, **payload})
            await bundle.step()
            bundle.req.valid.value = 0

        bundle.req.valid.value = 0
        bundle.rsp.ready.value = 1
        try:
            # Upstream get_resp() returns in the cycle where valid is observed.
            # Advance once with ready high so the prior response handshake is no
            # longer visible when this burst starts.
            for _ in range(8):
                await bundle.step()
                if not bool(bundle.rsp.valid.value) and bool(bundle.req.ready.value):
                    break

            await send_request(transactions[0])
            await wait_high(bundle.rsp.valid, "response backpressure")

            stalled_response = self._sample(bundle.rsp, ("cmd", "rdata"))
            second_payload = self._request_payload(transactions[1])
            bundle.rsp.ready.value = 0
            bundle.req.assign({"valid": 1, **second_payload})

            for _ in range(timeout_cycles):
                if not bool(bundle.rsp.valid.value):
                    response_payload_stable = False
                    break
                response_wait_cycles += 1
                response_payload_stable &= (
                    self._sample(bundle.rsp, ("cmd", "rdata")) == stalled_response
                )
                if not bool(bundle.req.ready.value):
                    input_wait_cycles += 1
                    request_payload_stable &= (
                        self._sample(bundle.req, ("addr", "size", "cmd", "wmask", "wdata"))
                        == second_payload
                    )
                await bundle.step()
                if (
                    input_wait_cycles > 0
                    and response_wait_cycles >= minimum_response_wait_cycles
                ):
                    break
            else:
                raise TimeoutError("backpressure burst timed out waiting for input backpressure")

            if not response_payload_stable:
                raise RuntimeError("response payload changed while valid was stalled")
            if input_wait_cycles == 0:
                raise TimeoutError("backpressure burst timed out waiting for input backpressure")

            second_handshake = bool(bundle.req.ready.value)
            bundle.rsp.ready.value = 1
            await bundle.step()
            responses.append(stalled_response)

            if not second_handshake:
                for _ in range(timeout_cycles):
                    if bool(bundle.req.ready.value):
                        break
                    input_wait_cycles += 1
                    request_payload_stable &= (
                        self._sample(bundle.req, ("addr", "size", "cmd", "wmask", "wdata"))
                        == second_payload
                    )
                    await bundle.step()
                else:
                    raise TimeoutError("backpressure burst timed out draining stalled request")
                await bundle.step()
            bundle.req.valid.value = 0

            await wait_high(bundle.rsp.valid, "second ordered response")
            responses.append(self._sample(bundle.rsp, ("cmd", "rdata")))
            await bundle.step()

            for transaction in transactions[2:]:
                await send_request(transaction)
                await wait_high(bundle.rsp.valid, "ordered response")
                responses.append(self._sample(bundle.rsp, ("cmd", "rdata")))
                await bundle.step()

            return BackpressureTrace(
                input_wait_cycles=input_wait_cycles,
                response_wait_cycles=response_wait_cycles,
                request_payload_stable=request_payload_stable,
                response_payload_stable=response_payload_stable,
                ordered_responses=len(responses) == len(transactions),
                responses=responses,
            )
        finally:
            bundle.req.valid.value = 0
            bundle.rsp.ready.value = 0
