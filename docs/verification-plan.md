# CacheSage-UC Verification Plan

This document is the working verification plan for the NutShell Cache target.
It is specific about the cache behavior being checked because a generic
read/write random test is too weak for this track.

## Scope

- Picker exposes the RTL as a Python-drivable DUT.
- Toffee organizes driver, monitor, reference model, scoreboard, and coverage.
- UCAgent helps draft stimulus, triage coverage holes, and explain failing seeds.
- Human review owns cache invariants, scoreboard rules, and evidence wording.

The plan avoids claiming multi-core coherence unless the target RTL and contest
materials expose that interface clearly. Replacement, dirty eviction, byte masks,
and stall stability are high priority because shallow AI-generated tests often
miss them.

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
| S11 | Mask and offset matrix | Full-word traffic hides byte-lane bugs. | Mix low mask, high mask, full mask, and non-zero word offsets. |
| S12 | Event-level replacement audit | Data still matches while policy state drifts. | Compare eviction address, writeback, refill, and stall events. |

## Planned Components

- `CacheDriver`: sends load/store requests with stable transaction IDs.
- `CacheMonitor`: records request, response, refill, writeback, stall, and reset-window events.
- `ReferenceMemory`: byte-addressable model used by the scoreboard.
- `CacheScoreboard`: checks data, event order, dirty writeback, replacement, and mask semantics.
- `CoverageCollector`: records functional coverpoints and produces JSON evidence.
- `PromptJournal`: stores UCAgent prompt rounds, rejected drafts, and human fixes.

The current repository contains both the evidence model and an executable Python
scoreboard rehearsal. The same interface is now prepared for the actual
Picker/Toffee DUT through `src/cachesage_uc/adapters/`.

## Coverage Policy

Coverage is counted only when a test both stimulates the behavior and checks the
observable effect. A random stream that happens to cause a replacement is not
credited unless the scoreboard also proves the victim behavior.

The current Python harness tracks 23 functional coverpoints. The local gate is:

```powershell
python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json
```

That run is expected to reach at least 90% Python harness coverage. RTL/Toffee
functional coverage is reported separately after the Picker-generated DUT is
available.
