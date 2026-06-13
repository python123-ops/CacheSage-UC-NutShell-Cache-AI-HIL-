# CacheSage-UC Verification Plan

This document is the working verification plan for the NutShell Cache target.
It is deliberately specific about the cache behavior being checked, because
generic "read/write random test" wording is not enough for this competition.

## Scope

The first target is a single-cache verification loop:

- Picker exposes the RTL as a Python-drivable DUT.
- Toffee organizes driver, monitor, reference model, scoreboard, and coverage.
- UCAgent is used for draft generation, failure explanation, and coverage-hole
  prompt rounds.
- Human review owns cache invariants and approves every scoreboard rule.

The plan avoids claiming multi-core coherence unless the target RTL and contest
material expose that interface clearly. Replacement and dirty eviction are high
priority because they are easy for shallow AI-generated tests to miss.

## Scenario Matrix

| ID | Scenario | Primary risk | Human check |
| --- | --- | --- | --- |
| S01 | Read/write smoke path | Driver or monitor wiring is wrong. | Compare every response with the reference memory model. |
| S02 | Read miss and refill | Refill order or replay response is wrong. | Check refill beat alignment and response timing. |
| S03 | Write miss allocate | Masked writes corrupt untouched bytes. | Read back full word and byte lanes after store. |
| S04 | Dirty eviction integrity | Dirty victim is dropped during replacement. | Require writeback before installing the new line. |
| S05 | Clean eviction silence | Clean victim creates a false writeback. | Monitor writeback channel quietness. |
| S06 | Replacement stress | Replacement state sticks or rotates incorrectly. | Bias addresses into one set and replay failing seeds. |
| S07 | Stall and back-pressure | Metadata changes while ready is low. | Assert request fields stay stable across stalls. |
| S08 | Reset recovery | Transient miss state leaks past reset. | Reset inside miss/refill windows, then run a clean smoke path. |
| S09 | Boundary address aliasing | Tag/index/offset slicing aliases neighbors. | Alternate adjacent lines and byte masks. |
| S10 | Long random regression | Rare interleavings escape directed tests. | Use seed, address distribution, write ratio, and stall knobs. |

## Planned Components

- `CacheDriver`: sends load/store requests with stable transaction IDs.
- `CacheMonitor`: records request, response, refill, and writeback events.
- `ReferenceMemory`: byte-addressable model used by the scoreboard.
- `CacheScoreboard`: checks data, event order, dirty writeback, and mask semantics.
- `CoverageCollector`: records functional coverpoints and produces JSON evidence.
- `PromptJournal`: stores UCAgent prompt rounds, rejected drafts, and human fixes.

The current repository contains the evidence model for these pieces. The next
code checkpoint should attach the components to the actual Picker/Toffee DUT.

## Coverage Policy

Coverage is counted only when a test both stimulates the behavior and checks the
observable effect. A random stream that happens to cause a replacement is not
credited unless the scoreboard also proves the victim behavior.

Target functional coverage for a competitive submission is 90 percent or higher,
but the report must show the measured result from the regression artifacts.
