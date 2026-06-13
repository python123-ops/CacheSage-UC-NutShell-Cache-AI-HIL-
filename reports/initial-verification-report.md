# CacheSage-UC Verification Evidence Report

This evidence package records the current CacheSage-UC state for the UCAgent NutShell Cache track. It separates planned verification intent, Python harness measurement, and the pending RTL/Toffee measurement gate.

## Evidence Boundary

| Evidence bucket | Status | Data now reported |
| --- | --- | --- |
| Planned functional coverage | Defined | 23 coverpoints across 12 scenarios |
| Python harness measured coverage | Measured | 23/23 (100.00%) on seed 11, 96 transactions |
| RTL/Toffee measured coverage | Pending | Reported only after Picker-generated DUT and Toffee smoke are installed locally |

## Executable Harness Snapshot

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` | PASS | 96 transactions, 100.00% measured coverpoints |

## Scenario Matrix

| ID | Scenario | Intent | Coverage |
| --- | --- | --- | --- |
| S01 | Read/write smoke path | Prove the Python driver, monitor, and scoreboard can close a simple cache transaction loop. | cp_read_hit, cp_write_hit_mask, cp_read_after_write |
| S02 | Read miss and refill | Exercise miss request, refill acceptance, and replayed response ordering. | cp_read_miss_refill, cp_refill_alignment |
| S03 | Write miss allocate | Check write-allocate behavior and byte mask preservation after a miss. | cp_write_miss_allocate, cp_write_hit_mask, cp_mask_mix |
| S04 | Dirty eviction integrity | Catch victim writeback loss before a replacement installs the new line. | cp_dirty_eviction, cp_writeback_observed, cp_refill_after_dirty_evict |
| S05 | Clean eviction silence | Make sure clean victims do not create phantom writebacks. | cp_clean_eviction, cp_replacement_rotation |
| S06 | Replacement stress | Stress set conflicts until replacement policy state errors become visible. | cp_replacement_rotation, cp_same_set_pressure, cp_long_random |
| S07 | Stall and back-pressure | Verify metadata is held stable while request, refill, or response channels stall. | cp_stall_hold, cp_refill_alignment |
| S08 | Reset recovery | Check that reset cancels transient cache activity before the next legal request. | cp_reset_recovery, cp_read_miss_refill |
| S09 | Boundary address aliasing | Defend against line-offset and tag slicing mistakes at boundary addresses. | cp_boundary_address, cp_offset_word_access, cp_write_hit_mask |
| S10 | Long random regression | Let coverage holes and scoreboard mismatches drive the next UCAgent prompt round. | cp_long_random, cp_dirty_eviction, cp_stall_hold, cp_multi_set_traffic |
| S11 | Mask and offset matrix | Expose byte-lane mistakes that full-word traffic can hide. | cp_partial_mask_low, cp_partial_mask_high, cp_full_line_mask, cp_mask_mix |
| S12 | Event-level replacement audit | Catch replacement-state drift even when architectural read data still matches. | cp_same_set_pressure, cp_writeback_observed, cp_refill_after_dirty_evict |

## AI 盲区与人工修正对比表

| Stage | AI output | Human correction | Lesson |
| --- | --- | --- | --- |
| Test-plan drafting | The first AI plan listed read/write hits and misses but treated replacement as a single generic case. | Split replacement into clean eviction, dirty eviction, and same-set pressure scenarios. | Coverage should name the cache invariant being protected, not just the operation category. |
| Scoreboard design | The generated checker compared only final read data and ignored writeback ordering. | Added a scoreboard obligation for victim writeback before refill installation. | Cache correctness depends on event order as much as end-state memory contents. |
| CRV constraints | The AI suggested uniform random addresses, which rarely hits replacement pressure quickly. | Biased address generation toward one set, then kept a smaller percentage of full-range traffic. | Good coverage comes from shaped randomness plus a few directed invariants. |
| Failure triage | The draft prompt asked the agent to fix any mismatch from the waveform summary directly. | Changed the flow so the human first classifies scoreboard bug, DUT bug, or stimulus bug. | Prompt tuning is useful after the failure has a credible engineering diagnosis. |
| Report hygiene | The AI-generated report phrased planned coverage as completed coverage. | Reworded the report to separate planned coverpoints, Python harness data, and RTL-measured results. | Competition reports should be ambitious, but the evidence must stay audit-friendly. |

## 故障注入

| Fault mode | Result | First failure summary |
| --- | --- | --- |
| `drop_dirty_writeback` | FAIL as expected | memory mismatch at 0x0: expected 0xDEADBEEF, observed 0x00000000 |
| `ignore_write_mask` | FAIL as expected | data mismatch at 0x0: expected 287493341, observed 2864434397 |
| `stuck_replacement` | FAIL as expected | eviction sequence mismatch: expected [('miss', 96, ''), ('eviction', 32, 'clean'), ('refill', 96, ''), ('read', 96, 'replace-evict-b')], observed [('miss', 96, ''), ('eviction', 64, 'clean'), ('refill', 96, ''), ('read', 96, 'replace-evict-b')] |
| `refill_shift` | FAIL as expected | data mismatch at 0x0: expected 287454020, observed 0 |
| `unstable_under_stall` | FAIL as expected | data mismatch at 0x0: expected 3405691582, observed 3405691457 |

## Fault Model Catalog

- drop_dirty_writeback: dirty victim data is not written back before replacement
- ignore_write_mask: byte mask is ignored on store hit
- stuck_replacement: replacement pointer does not advance after eviction
- refill_shift: refill beat index is shifted by one word
- unstable_under_stall: request metadata/data changes while downstream ready is low

## Next Regression Gate

Connect these scenarios to the Picker-generated Python DUT, run the Toffee environment with deterministic seeds, and add RTL-measured functional coverage plus waveform-backed failure artifacts. Until that gate runs, this report deliberately avoids claiming real NutShell RTL bugs.
