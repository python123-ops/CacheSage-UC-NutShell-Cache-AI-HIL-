import os
from pathlib import Path

import toffee_test
from Cache import DUTCache
from env.bundle import SimpleBusBundle
from env.ntcache_env import NtCacheEnv
from env.simpleram import SimpleBusRam
from toffee import ClockCycles, Executor, start_clock
from toffee.logger import ERROR, setup_logging
from utils.cmd_code import CMD_READ, CMD_READBST, CMD_WRITE, CMD_WRITEBST, CMD_WRITELST
from utils.common import replicate_bits


class TracedSimpleBusRam(SimpleBusRam):
    def __init__(self, agent, response_latency_cycles=2):
        super().__init__(agent)
        self.requests = []
        self.response_latency_cycles = response_latency_cycles

    async def _delay(self):
        for _ in range(self.response_latency_cycles):
            await self.agent.bundle.step()

    async def _write_burst(self, request):
        address = request["addr"]
        while True:
            self.requests.append(dict(request))
            data = request["wdata"]
            write_mask = replicate_bits(request["wmask"], 8, 8)
            self.data[address] = (self.data.get(address, 0) & ~write_mask) | (data & write_mask)
            await self._delay()
            await self.agent.write_resp()
            if request["cmd"] == CMD_WRITELST:
                return
            request = await self.agent.get_req()
            address += 8

    async def rsp_once(self):
        request = await self.agent.get_req()
        if request["cmd"] in {CMD_READBST, CMD_READ}:
            self.requests.append(dict(request))
            first_address = request["addr"] & 0xFFFFFFC0
            word = (request["addr"] - first_address) >> 3
            data = []
            for _ in range(1 << request["size"]):
                data.append(self.data.get(first_address + (word << 3), 0))
                word = (word + 1) % (1 << request["size"])
            await self._delay()
            await self.agent.read_resp(request["size"], data)
        elif request["cmd"] == CMD_WRITEBST:
            await self._write_burst(request)
        elif request["cmd"] == CMD_WRITE:
            self.requests.append(dict(request))
            address = request["addr"] & 0xFFFFFFF8
            write_mask = replicate_bits(request["wmask"], 8, 8)
            self.data[address] = (self.data.get(address, 0) & ~write_mask) | (request["wdata"] & write_mask)
            await self._delay()
            await self.agent.write_resp()


@toffee_test.fixture
async def rtl_cache(toffee_request: toffee_test.ToffeeRequest):
    setup_logging(ERROR)
    artifact_dir = Path(os.environ.get("CACHESAGE_RTL_ARTIFACT_DIR", "artifacts/rtl"))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dut = toffee_request.create_dut(
        DUTCache,
        "clock",
        waveform_filename=str(artifact_dir / "nutshell-cache-regression.fst"),
        coverage_filename=str(artifact_dir / "coverage.dat"),
    )
    env = NtCacheEnv(dut)
    env.dut = dut
    env.mem_ram = TracedSimpleBusRam(env.mem_agent)
    env.mem_trace = env.mem_ram.requests
    env.mem_latency_cycles = env.mem_ram.response_latency_cycles
    env.victim_masks = []

    async def monitor_victim_way():
        while True:
            await ClockCycles(dut, 1)
            if dut.victim_way_mask_valid.value:
                env.victim_masks.append(int(dut.victim_way_mask.value))

    async def start():
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        start_clock(dut)
        await ClockCycles(dut, 100)
        dut.reset.value = 0
        dut.io_flush.value = 0
        async with Executor(exit="none") as executor:
            executor(env.mem_ram.work(), sche_group="memory")
            executor(SimpleBusRam(env.mmio_agent).work(), sche_group="mmio")
            executor(monitor_victim_way(), sche_group="victim-way-monitor")
        return env

    return start
