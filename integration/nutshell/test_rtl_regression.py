import importlib.metadata
import os
import subprocess
from pathlib import Path

import toffee_test
from env.bundle import SimpleBusBundle
from env.simplebus_agents import SimpleBusMasterAgent
from toffee import ClockCycles
from utils.cmd_code import (
    CMD_PROBE,
    CMD_PROBEHIT,
    CMD_PROBEMISS,
    CMD_READ,
    CMD_READBST,
    CMD_READLST,
    CMD_WRITE,
    CMD_WRITEBST,
    CMD_WRITELST,
)

from cachesage_uc.adapters.nutshell_runtime import NutShellRequestDriver
from cachesage_uc.rtl_coverage import RtlCoverageCollector, RtlObservation
from cachesage_uc.rtl_evidence import build_rtl_evidence, write_rtl_evidence
from cachesage_uc.rtl_verification import (
    RTL_CACHE_CONFIG,
    RtlScoreboard,
    RtlTransaction,
    build_rtl_directed_sequence,
    build_rtl_random_sequence,
)


READ_COMMANDS = {CMD_READ, CMD_READBST}
WRITE_COMMANDS = {CMD_WRITE, CMD_WRITEBST, CMD_WRITELST}


def _tool_version(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _upstream_commit():
    upstream = Path(os.environ["CACHESAGE_UPSTREAM"])
    return subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()


@toffee_test.testcase
async def test_rtl_functional_coverage(rtl_cache):
    env = await rtl_cache()
    driver = NutShellRequestDriver(env.in_agent, CMD_READ, CMD_WRITE)
    coherence = SimpleBusMasterAgent(
        SimpleBusBundle.from_prefix("io_out_coh_").set_name("coherence").bind(env.dut)
    )
    coverage = RtlCoverageCollector()
    scoreboard = RtlScoreboard()
    seen_lines_by_set = {}
    seen_sets = set()
    written_words = set()
    transaction_count = 0

    async def access(transaction, seed, index, reset_recovered=False):
        nonlocal transaction_count
        memory_start = len(env.mem_trace)
        victim_start = len(env.victim_masks)
        response = await driver.execute(transaction)
        memory_events = env.mem_trace[memory_start:]
        victim_events = env.victim_masks[victim_start:]
        memory_read = any(event["cmd"] in READ_COMMANDS for event in memory_events)
        memory_write = any(event["cmd"] in WRITE_COMMANDS for event in memory_events)
        line = RTL_CACHE_CONFIG.line_base(transaction.address)
        set_index = RTL_CACHE_CONFIG.set_index(transaction.address)
        lines = seen_lines_by_set.setdefault(set_index, set())
        lines.add(line)
        seen_sets.add(set_index)
        hit = not memory_read
        read_after_write = transaction.op == "read" and transaction.address in written_words
        observed_data = response.get("rdata") if transaction.op == "read" else None
        scoreboard.observe(transaction, observed_data, seed, index)
        if transaction.op == "write":
            written_words.add(transaction.address)
        source_events = []
        if memory_read:
            source_events.append("mem-read")
        if memory_write:
            source_events.append("mem-write")
        if victim_events:
            source_events.append(f"victim-{victim_events[-1]:x}")
        source = f"seed-{seed}:tx-{index}:{transaction.tag or transaction.op}"
        if source_events:
            source += ":" + "+".join(source_events)
        replacement = len(lines) > RTL_CACHE_CONFIG.ways and memory_read
        coverage.observe(
            RtlObservation(
                op=transaction.op,
                address=transaction.address,
                mask=transaction.mask,
                hit=hit,
                memory_read=memory_read,
                memory_write=memory_write,
                refill=memory_read,
                victim_way=victim_events[-1] if victim_events else 0,
                dirty_eviction=memory_write,
                clean_eviction=replacement and not memory_write,
                writeback=memory_write,
                read_after_write=read_after_write,
                same_set_depth=len(lines),
                set_count=len(seen_sets),
                memory_read_wait_cycles=env.mem_latency_cycles if memory_read else 0,
                memory_write_wait_cycles=env.mem_latency_cycles if memory_write else 0,
                reset_recovered=reset_recovered,
                source=source,
            )
        )
        transaction_count += 1
        return response

    async def probe(address, source, expected_dirty=False, after_eviction=False):
        nonlocal transaction_count
        env.dut.io_in_resp_ready.value = 1
        await coherence.send_req(address, 3, CMD_PROBE)
        response = await coherence.get_resp()
        release_data = []
        if response["cmd"] == CMD_PROBEHIT:
            for _ in range(8):
                beat = await coherence.get_resp()
                release_data.append(beat["rdata"])
                if beat["cmd"] == CMD_READLST:
                    break
        env.dut.io_in_resp_ready.value = 0
        result = "miss" if response["cmd"] == CMD_PROBEMISS else (
            "dirty_hit" if expected_dirty else "clean_hit"
        )
        coverage.observe(
            RtlObservation(
                op="probe",
                address=address,
                probe_result=result,
                probe_data_returned=bool(release_data),
                probe_after_write=expected_dirty,
                probe_after_eviction=after_eviction and result == "miss",
                source=source,
            )
        )
        transaction_count += 1
        return result, release_data

    directed = [tx for tx in build_rtl_directed_sequence() if tx.op != "probe"]
    for index, transaction in enumerate(directed):
        await access(transaction, seed=0, index=index, reset_recovered=index == 0)
    print(f"directed-complete transactions={transaction_count}", flush=True)

    clean_set_base = 0x0100
    for tag in range(6):
        await access(
            RtlTransaction.read(clean_set_base + tag * RTL_CACHE_CONFIG.same_set_stride, f"clean-evict-{tag}"),
            seed=0,
            index=len(directed) + tag,
        )
    print(f"clean-eviction-complete transactions={transaction_count}", flush=True)

    miss_result, _ = await probe(0x00180000, "probe-miss")
    assert miss_result == "miss"
    print("probe-miss-complete", flush=True)
    await access(RtlTransaction.read(0x00012000, "probe-clean-fill"), 0, 100)
    clean_result, _ = await probe(0x00012000, "probe-clean-hit")
    assert clean_result == "clean_hit"
    print("probe-clean-complete", flush=True)
    await access(RtlTransaction.write(0x00014000, 0xAABBCCDDEEFF0011, tag="probe-dirty-fill"), 0, 101)
    dirty_result, release_data = await probe(0x00014000, "probe-after-write", expected_dirty=True)
    assert dirty_result == "dirty_hit"
    assert 0xAABBCCDDEEFF0011 in release_data
    print("probe-dirty-complete", flush=True)
    reaccess = await access(RtlTransaction.read(0x00014000, "probe-reaccess"), 0, 102)
    assert reaccess["rdata"] == 0xAABBCCDDEEFF0011
    coverage.observe(
        RtlObservation(op="probe", address=0x00014000, probe_reaccess=True, source="probe-reaccess")
    )
    print("probe-reaccess-complete", flush=True)

    eviction_base = 0x00000300
    eviction_candidates = []
    for tag in range(8):
        address = eviction_base + tag * RTL_CACHE_CONFIG.same_set_stride
        eviction_candidates.append(address)
        await access(RtlTransaction.read(address, f"probe-eviction-fill-{tag}"), 0, 110 + tag)
    print("probe-eviction-fill-complete", flush=True)
    observed_eviction = False
    for address in eviction_candidates:
        result, _ = await probe(address, f"probe-after-eviction-{address:x}", after_eviction=True)
        if result == "miss":
            observed_eviction = True
            break
    assert observed_eviction
    print(f"probe-suite-complete transactions={transaction_count}", flush=True)

    seeds = [11, 29, 73]
    for seed in seeds:
        for index, transaction in enumerate(build_rtl_random_sequence(seed, 128)):
            await access(transaction, seed=seed, index=index)
            if (index + 1) % 32 == 0:
                print(f"seed-{seed} progress={index + 1}/128", flush=True)

    idle_empty = False
    for _ in range(1024):
        await ClockCycles(env.dut, 1)
        if env.dut.io_empty.value:
            idle_empty = True
            break
    coverage.observe(
        RtlObservation(op="read", address=0, idle_empty=idle_empty, source="io-empty-signal")
    )
    assert idle_empty

    report = coverage.report(scoreboard.comparisons, scoreboard.failures)
    artifact_dir = Path(os.environ["CACHESAGE_RTL_ARTIFACT_DIR"])
    output_json = Path(os.environ["CACHESAGE_RTL_OUTPUT_JSON"])
    output_markdown = Path(os.environ["CACHESAGE_RTL_OUTPUT_MARKDOWN"])
    evidence = build_rtl_evidence(
        report,
        upstream_commit=_upstream_commit(),
        tools={
            "picker": os.environ.get("CACHESAGE_PICKER_VERSION", "installed from source"),
            "toffee": _tool_version("pytoffee"),
            "toffee-test": _tool_version("toffee-test"),
            "verilator": os.environ.get("CACHESAGE_VERILATOR_VERSION", "unknown"),
        },
        seeds=seeds,
        transactions=transaction_count,
        waveform=str(artifact_dir / "nutshell-cache-regression.fst"),
        code_coverage={
            "status": "collection_requested",
            "artifact": str(artifact_dir / "coverage.dat"),
        },
    )
    write_rtl_evidence(evidence, output_json, output_markdown)
    assert not scoreboard.failures
    assert report.covered >= 33, f"RTL functional coverage is {report.covered}/{report.total}"
