# Fault-Injection Plan

Fault injection is included to prove the verification environment can catch
realistic cache bugs. These injections are testbench validation tools, not claims
about existing NutShell defects.

| Fault ID | Injected behavior | Expected detector | Useful scenario |
| --- | --- | --- | --- |
| F01 | Replacement state does not advance after refill. | Coverage and scoreboard observe repeated victim choice under same-set pressure. | S06 |
| F02 | Dirty bit clears before victim writeback is accepted. | Scoreboard requires writeback event before replacement completes. | S04 |
| F03 | Refill beat index is shifted by one word. | Reference model readback detects line-lane mismatch. | S02 |
| F04 | Write mask is ignored on store hit. | Byte-lane readback shows untouched bytes changed. | S03 |
| F05 | Request metadata changes while ready is low. | Monitor assertion catches unstable address, mask, or command. | S07 |

## Acceptance Rule

Each injected fault should have at least one deterministic seed that fails for
the intended reason. A useful failure artifact contains:

- seed and scenario ID;
- transaction trace summary;
- scoreboard assertion or monitor assertion;
- waveform pointer when available;
- short human diagnosis before asking UCAgent for a patch suggestion.
