# Fault-Injection Plan

Fault injection is included to prove the verification environment can catch
realistic cache mistakes. These injections validate the testbench; they are not
claims about existing NutShell defects.

| Fault mode | Injected behavior | Expected detector | Deterministic entry |
| --- | --- | --- | --- |
| `drop_dirty_writeback` | Dirty victim data is not written back before replacement. | Final memory mismatch plus missing writeback event. | `build_fault_sequence(FaultMode.DROP_DIRTY_WRITEBACK)` |
| `ignore_write_mask` | Store hit ignores byte mask and overwrites all lanes. | Readback data mismatch on untouched bytes. | `build_fault_sequence(FaultMode.IGNORE_WRITE_MASK)` |
| `stuck_replacement` | Replacement pointer does not advance under same-set pressure. | Event-level scoreboard sees wrong eviction address. | `build_fault_sequence(FaultMode.STUCK_REPLACEMENT)` |
| `refill_shift` | Refill data is shifted by one word. | Readback data mismatch after dirty line is evicted and refilled. | `build_fault_sequence(FaultMode.REFILL_SHIFT)` |
| `unstable_under_stall` | Data mutates while a stall-tagged request is held. | Readback data mismatch and `unstable_under_stall` event. | `build_fault_sequence(FaultMode.UNSTABLE_UNDER_STALL)` |

## Acceptance Rule

Each injected fault must have at least one deterministic sequence that fails for
the intended reason. A useful failure artifact contains:

- fault mode and deterministic seed or directed sequence name;
- transaction trace summary;
- first scoreboard or monitor failure;
- coverage points touched by the failure path;
- short human diagnosis before asking UCAgent for a patch suggestion.

Current executable evidence:

- `tests/test_verification_core.py::test_each_fault_mode_has_a_deterministic_detecting_sequence`
  verifies all five modes.
- `reports/fault-drop-dirty-writeback.json` is a sample JSON artifact for the
  dirty victim loss case.
- The report generator renders a fault matrix without claiming any real RTL bug.
