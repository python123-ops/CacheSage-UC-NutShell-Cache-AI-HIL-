# Review Catalog

This catalog records review findings that changed the verification plan or the
testbench implementation.

| ID | Review finding | Correction | Evidence |
| --- | --- | --- | --- |
| RV-001 | Replacement was treated as one generic case. | Split clean eviction, dirty eviction, and same-set pressure. | `docs/verification-plan.md`, `tests/test_verification_core.py` |
| RV-002 | Uniform random addresses were proposed. | Added a directed coverage spine before the random tail. | `build_seeded_random_sequence(seed=11,count=96)` |
| RV-003 | Fault injection focused only on dirty writeback and masks. | Added `stuck_replacement`, `refill_shift`, and `unstable_under_stall`. | `test_each_fault_mode_has_a_deterministic_detecting_sequence` |
| RV-004 | Report wording blurred planned coverage and measured RTL coverage. | Split evidence into planned, Python harness measured, and RTL/Toffee measured buckets. | `reports/initial-verification-report.md` |
| RV-005 | Adapter design was initially guessed without reading upstream shape. | Locked Example-NutShellCache commit and added layout inspection before smoke. | `upstream.lock.json`, `docs/upstream-survey.md` |

The JSONL version in `review_journal.jsonl` is the machine-readable source used
by tests and report review.
