# CacheSage-UC Initial Verification Report

This report is the initial evidence package for the UCAgent NutShell Cache track. It records the verification intent, executable Python harness results, AI-human review trail, and fault-injection targets before the RTL Picker/Toffee binding is attached.

## Verification Scope

- DUT: NutShell Cache
- Scenarios: 10
- Coverage points tracked: 0/12 (0.00%)
- Executable harness smoke run: PASS, 10/12 planned coverpoints (83.33%).
- Current status: the Python verification core is runnable; RTL-measured coverage is reported separately once Picker/Toffee runs are wired in.

## Executable Harness Snapshot

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m cachesage_uc.cli run --seed 11 --count 48 --output reports/sample-run-seed11.json` | PASS | 48 transactions, 83.33% planned coverpoints |
| `python -m cachesage_uc.cli run --seed 11 --count 48 --fault drop_dirty_writeback --output reports/fault-drop-dirty-writeback.json` | FAIL as expected | Scoreboard detects dirty victim writeback loss |

## Scenario Matrix

| ID | Scenario | Intent | Coverage |
| --- | --- | --- | --- |
| S01 | Read/write smoke path | Prove the Python driver, monitor, and scoreboard can close a simple cache transaction loop. | cp_read_hit, cp_write_hit_mask |
| S02 | Read miss and refill | Exercise miss request, refill acceptance, and replayed response ordering. | cp_read_miss_refill, cp_refill_alignment |
| S03 | Write miss allocate | Check write-allocate behavior and byte mask preservation after a miss. | cp_write_miss_allocate, cp_write_hit_mask |
| S04 | Dirty eviction integrity | Catch victim writeback loss before a replacement installs the new line. | cp_dirty_eviction, cp_replacement_rotation |
| S05 | Clean eviction silence | Make sure clean victims do not create phantom writebacks. | cp_clean_eviction, cp_replacement_rotation |
| S06 | Replacement stress | Stress set conflicts until replacement policy state errors become visible. | cp_replacement_rotation, cp_long_random |
| S07 | Stall and back-pressure | Verify metadata is held stable while request, refill, or response channels stall. | cp_stall_hold, cp_refill_alignment |
| S08 | Reset recovery | Check that reset cancels transient cache activity before the next legal request. | cp_reset_recovery, cp_read_miss_refill |
| S09 | Boundary address aliasing | Defend against line-offset and tag slicing mistakes at boundary addresses. | cp_boundary_address, cp_write_hit_mask |
| S10 | Long random regression | Let coverage holes and scoreboard mismatches drive the next UCAgent prompt round. | cp_long_random, cp_dirty_eviction, cp_stall_hold |

## AI 缺陷与人工修正对比表

| Stage | AI output | Human correction | Lesson |
| --- | --- | --- | --- |
| Test-plan drafting | The first AI plan listed read/write hits and misses but treated replacement as a single generic case. | Split replacement into clean eviction, dirty eviction, and same-set pressure scenarios. | Coverage should name the cache invariant being protected, not just the operation category. |
| Scoreboard design | The generated checker compared only final read data and ignored writeback ordering. | Added a scoreboard obligation for victim writeback before refill installation. | Cache correctness depends on event order as much as end-state memory contents. |
| CRV constraints | The AI suggested uniform random addresses, which rarely hits replacement pressure quickly. | Biased address generation toward one set, then kept a smaller percentage of full-range traffic. | Good coverage comes from shaped randomness plus a few directed invariants. |
| Failure triage | The draft prompt asked the agent to fix any mismatch from the waveform summary directly. | Changed the flow so the human first classifies scoreboard bug, DUT bug, or stimulus bug. | Prompt tuning is useful after the failure has a credible engineering diagnosis. |
| Report hygiene | The AI-generated report phrased planned coverage as completed coverage. | Reworded the initial report to separate planned coverpoints from RTL-measured results. | Competition reports should be ambitious, but the evidence must stay audit-friendly. |

## 故障注入

- Replacement state does not advance after a refill
- Dirty bit is cleared before victim writeback is accepted
- Refill beat index is shifted by one word
- Write mask is ignored on store hit
- Request metadata changes while downstream ready is low

## Next Regression Gate

The next gate is to connect these scenarios to the Picker-generated Python DUT, run the Toffee environment with deterministic seeds, and replace the harness-only coverage with RTL-measured functional coverage plus waveform-backed failure artifacts.
