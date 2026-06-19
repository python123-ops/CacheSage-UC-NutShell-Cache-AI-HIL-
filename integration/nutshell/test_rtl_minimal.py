import toffee_test
from env.bundle import SimpleBusBundle
from env.simplebus_agents import SimpleBusMasterAgent
from utils.cmd_code import CMD_PROBE, CMD_PROBEHIT, CMD_PROBEMISS, CMD_READ, CMD_READLST, CMD_WRITE

from cachesage_uc.adapters.nutshell_runtime import NutShellRequestDriver
from cachesage_uc.rtl_verification import RtlTransaction


@toffee_test.testcase
async def test_real_dut_read_write_read(rtl_cache):
    env = await rtl_cache()
    driver = NutShellRequestDriver(env.in_agent, CMD_READ, CMD_WRITE)
    address = 0x1000
    initial = await driver.execute(RtlTransaction.read(address))
    write_response = await driver.execute(RtlTransaction.write(address, 0x1122334455667788))
    observed = await driver.execute(RtlTransaction.read(address))

    assert initial["rdata"] == 0
    assert write_response["cmd"] >= 0
    assert observed["rdata"] == 0x1122334455667788


@toffee_test.testcase
async def test_real_dut_coherence_probe(rtl_cache):
    env = await rtl_cache()
    driver = NutShellRequestDriver(env.in_agent, CMD_READ, CMD_WRITE)
    coherence = SimpleBusMasterAgent(
        SimpleBusBundle.from_prefix("io_out_coh_").set_name("coherence").bind(env.dut)
    )
    env.dut.io_in_resp_ready.value = 1

    await coherence.send_req(0x4000, 7, CMD_PROBE)
    missing = await coherence.get_resp()
    assert missing["cmd"] == CMD_PROBEMISS

    env.dut.io_in_resp_ready.value = 0
    await driver.execute(RtlTransaction.write(0x4000, 0xAABBCCDDEEFF0011))
    normal_read = await driver.execute(RtlTransaction.read(0x4000))
    assert normal_read["rdata"] == 0xAABBCCDDEEFF0011
    env.dut.io_in_resp_ready.value = 1
    await coherence.send_req(0x4000, 3, CMD_PROBE)
    dirty = await coherence.get_resp()
    assert dirty["cmd"] == CMD_PROBEHIT
    release_data = []
    for _ in range(8):
        beat = await coherence.get_resp()
        release_data.append(beat["rdata"])
        if beat["cmd"] == CMD_READLST:
            break
    assert 0xAABBCCDDEEFF0011 in release_data
