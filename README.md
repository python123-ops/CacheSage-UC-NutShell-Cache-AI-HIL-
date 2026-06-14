# CacheSage-UC

CacheSage-UC is a coverage-guided verification project for the UCAgent NutShell
Cache track. It keeps the verification work reviewable: cache invariants are
written down, the Python harness is reproducible, and RTL/Toffee results are
reported separately from the local model results.

中文简介：CacheSage-UC 面向 NutShell Cache 验证场景，围绕 Picker、Toffee 和
Python harness 建立一套可复现的验证记录。当前仓库已经包含可运行的参考 Cache
模型、Scoreboard、CRV 事务生成、5 类故障注入、23 个功能覆盖点、上游
Example-NutShellCache 锁定脚本，以及人工复盘记录。

## Current Engineering Status

| Layer | Status | Evidence |
| --- | --- | --- |
| Python verification harness | Runnable | `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` |
| Functional coverage model | 23 coverpoints | read/write hit, refill, dirty/clean eviction, mask, stall, reset, same-set pressure |
| Fault injection | 5 deterministic modes | `drop_dirty_writeback`, `ignore_write_mask`, `stuck_replacement`, `refill_shift`, `unstable_under_stall` |
| NutShell upstream alignment | Pinned, not vendored | `upstream.lock.json`, `scripts/fetch_upstream_example.py` |
| Picker/Toffee bridge | Adapter boundary present | `src/cachesage_uc/adapters/`, `scripts/run_nutshell_smoke.py` |
| RTL-measured coverage | Not claimed yet | Reported only after local Picker/Toffee dependencies are installed |

This project does not claim that the real NutShell RTL has a bug. The current
fault results are injected-fault checks used to validate the harness and
scoreboard.

## Verification Capability

| Area | Current implementation |
| --- | --- |
| Cache behavior | Read/write hit, miss/refill, write-allocate, byte masks, dirty and clean eviction. |
| Control stress | Same-set pressure, replacement rotation, stall windows, reset recovery, and boundary offsets. |
| Scoreboard | Read data, final backing memory, and event signature comparisons. |
| Review trail | `review_journal.jsonl` and `docs/review-catalog.md` record draft issues and human corrections. |
| Integration boundary | Upstream layout inspection plus Toffee-style request case mapping. |

## Reproducible Commands

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
python -m cachesage_uc.cli plan
python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json
python scripts/generate_report.py --output reports/initial-verification-report.md
```

The current tooling layer uses only the Python standard library. Picker/Toffee
are needed only for the RTL smoke path.

## NutShell / Toffee Preparation

```powershell
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache --dry-run
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
```

If the upstream example or local Picker/Toffee dependencies are missing,
`run_nutshell_smoke.py` exits with a clear setup hint and writes a
machine-readable status file. This does not block the base Python regression.

## Repository Layout

```text
src/cachesage_uc/        Verification core, evidence model, CLI, and adapters.
tests/                   Standard-library regression tests.
docs/                    Verification plan, upstream survey, Toffee flow, review notes.
examples/                Machine-readable sample evidence.
reports/                 Generated and curated verification records.
scripts/                 Report, upstream fetch, and smoke helpers.
review_journal.jsonl     Prompt / draft / review correction records.
upstream.lock.json       Pinned Example-NutShellCache source identity.
```

## Next Integration Checkpoint

The next checkpoint is to run the same scenario matrix against the
Picker-generated NutShell Cache Python DUT, then add RTL/Toffee measured
coverage and waveform-backed failure artifacts. Until that gate runs, the report
keeps Python harness coverage and RTL coverage in separate rows.

## License

Apache License 2.0. See [LICENSE](LICENSE).
