# AI Defect Catalog

This catalog is the human-review side of the AI-HIL story. It records places
where AI-generated verification ideas were useful but incomplete.

| ID | AI blind spot | Human correction | Evidence |
| --- | --- | --- | --- |
| HIL-001 | Replacement was treated as one generic case. | Split clean eviction, dirty eviction, and same-set pressure. | `docs/verification-plan.md`, `tests/test_verification_core.py` |
| HIL-002 | Uniform random addresses were proposed. | Added a directed coverage spine before the random tail. | `build_seeded_random_sequence(seed=11,count=96)` |
| HIL-003 | Fault injection focused only on dirty writeback and masks. | Added `stuck_replacement`, `refill_shift`, and `unstable_under_stall`. | `test_each_fault_mode_has_a_deterministic_detecting_sequence` |
| HIL-004 | Report wording blurred planned coverage and measured RTL coverage. | Split evidence into planned, Python harness measured, and RTL/Toffee measured buckets. | `reports/initial-verification-report.md` |
| HIL-005 | Adapter design was initially guessed without reading upstream shape. | Locked Example-NutShellCache commit and added layout inspection before smoke. | `upstream.lock.json`, `docs/upstream-survey.md` |

The JSONL version in `ai_hil_log.jsonl` is the machine-readable source used by
tests and report review.
