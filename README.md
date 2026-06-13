# CacheSage-UC

CacheSage-UC is a coverage-guided AI-HIL verification project for the UCAgent
NutShell Cache track. It focuses on one practical question: can an AI-assisted
verification loop produce reviewable cache evidence instead of only a polished
plan?

中文简介：CacheSage-UC 面向 NutShell Cache 验证场景，围绕 Picker / Toffee /
Python harness 建立一套可复现的 AI-HIL 验证证据链。当前仓库已经包含可运行的参考
Cache 模型、Scoreboard、CRV 事务生成、5 类故障注入、23 个功能覆盖点、上游
Example-NutShellCache 锁定脚本，以及人工修正 AI 盲区的证据日志。

## Current Status

| Layer | Status | Evidence |
| --- | --- | --- |
| Python verification harness | Runnable | `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` |
| Functional coverage model | 23 coverpoints | read/write hit, refill, dirty/clean eviction, mask, stall, reset, same-set pressure |
| Fault injection | 5 deterministic modes | `drop_dirty_writeback`, `ignore_write_mask`, `stuck_replacement`, `refill_shift`, `unstable_under_stall` |
| NutShell upstream alignment | Pinned, not vendored | `upstream.lock.json`, `scripts/fetch_upstream_example.py` |
| Picker/Toffee bridge | Adapter boundary present | `src/cachesage_uc/adapters/`, `scripts/run_nutshell_smoke.py` |
| RTL-measured coverage | Not claimed yet | Reported only after local Picker/Toffee dependencies are installed |

This project does not claim that the real NutShell RTL has a bug. The current
fault results are injected-fault checks used to prove the verification
environment can detect meaningful cache mistakes.

## Why This Project Should Score Well

| Competition dimension | CacheSage-UC response |
| --- | --- |
| Completeness | Covers read/write hits, misses, refill, dirty eviction, clean eviction, replacement pressure, stalls, reset recovery, boundary offsets, masks, and long seeded CRV streams. |
| Technical depth | Uses a reference memory model, event-level scoreboard checks, deterministic fault seeds, upstream layout inspection, and a Toffee case adapter. |
| AI usage efficiency | Keeps `ai_hil_log.jsonl` and `docs/ai-defect-catalog.md` so reviewers can see where AI helped and where human verification judgment corrected it. |
| Engineering quality | Apache-2.0, standard-library tests, reproducible commands, locked upstream commit, no large vendored third-party source, and generated reports under version control. |

## Quick Start

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

If the upstream example has not been fetched, `run_nutshell_smoke.py` exits with
a clear setup hint and writes a machine-readable status file. It does not block
the base Python regression.

## Repository Layout

```text
src/cachesage_uc/        Verification core, evidence model, CLI, and adapters.
tests/                   Standard-library regression tests.
docs/                    Verification plan, upstream survey, Toffee flow, AI-HIL evidence.
examples/                Machine-readable sample evidence.
reports/                 Generated and curated competition reports.
scripts/                 Report, upstream fetch, and smoke helpers.
ai_hil_log.jsonl         Prompt / AI output / human correction evidence.
upstream.lock.json       Pinned Example-NutShellCache source identity.
```

## Verification Direction

The next competition checkpoint is to run the same scenario matrix against the
Picker-generated NutShell Cache Python DUT, then add RTL/Toffee measured
coverage and waveform-backed failure artifacts. Until that gate runs, the report
keeps Python harness coverage and RTL coverage in separate rows.

## License

Apache License 2.0. See [LICENSE](LICENSE).
