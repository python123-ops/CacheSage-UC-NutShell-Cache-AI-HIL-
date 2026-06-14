# Scoreboard Design Notes

The scoreboard is the part of this project where I want the most human review.
Cache bugs are often not "wrong data immediately" bugs. They can be event-order
bugs: a dirty victim is written too late, a refill overwrites a live line, or a
stall lets request metadata drift while the data path looks fine in a short run.

## Current Executable Harness

The current Python harness is intentionally small and reviewable:

- `Transaction` represents aligned read/write operations and byte masks.
- `CacheModel` is a set-associative cache with dirty bits, refill, replacement,
  writeback, and optional fault modes.
- `VerificationRunner` runs the same sequence through a golden model and a
  candidate model, then compares read responses, final backing memory, and
  monitor event signatures.
- Coverage is derived from observed transactions and cache events, not from a
  hand-written checklist alone.

This is not a replacement for the final Picker/Toffee DUT binding. It is a
scoreboard rehearsal: the rules are executable before the RTL adapter lands.

## Invariants Owned By Human Review

| Invariant | Why it matters | Current detector |
| --- | --- | --- |
| Masked writes preserve unselected bytes. | Store data can look correct on selected lanes while corrupting neighbors. | Readback against reference memory. |
| Dirty victim writeback happens before replacement completes. | End-state data can be lost even if the immediate refill succeeds. | Final memory comparison plus writeback event coverage. |
| Replacement rotates under same-set pressure. | Naive random traffic may never expose replacement state bugs. | Same-set constrained stream plus eviction-address event comparison. |
| Refill events align to the requested line. | Beat indexing bugs often show only on line offsets. | Refill event plus readback coverage. |
| Stall windows keep metadata/data stable. | A short architectural readback can miss a handshake stability bug. | Stall-tagged transactions plus event-level scoreboard failure. |
| Scoreboard failures are classified before patching. | A quick fix can hide a scoreboard bug or stimulus bug. | Review journal and fault JSON artifacts. |

## Planned Toffee Mapping

The Python harness maps cleanly to the final Toffee components:

- `Transaction` becomes the generator item.
- `CacheModel` becomes the reference model.
- cache events become monitor observations from request, response, refill, and
  writeback channels.
- `VerificationRunner` becomes the regression wrapper that stores seed, coverage,
  and failure artifacts.

The rule I will keep during the RTL step: no coverpoint is counted unless there
is also an observable scoreboard or monitor check behind it.
