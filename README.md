# CacheSage-UC

CacheSage-UC is a coverage-guided AI-HIL verification suite for the NutShell
Cache track of the UCAgent competition. The project is built around a simple
principle: UCAgent can accelerate testbench creation, but cache verification
still needs human-owned invariants, constrained random design, scoreboard
reviews, and honest coverage evidence.

中文简介：CacheSage-UC 是一个基于 UCAgent、Picker 与 Toffee 思路构建的
NutShell Cache 验证项目。当前仓库先交付可复现的验证计划、覆盖率证据模型、
AI/人工协同记录和报告生成工具，后续把这些场景接到 Picker 导出的 Python DUT
和 Toffee 验证环境中。

## Current Status

This repository is at the first engineering checkpoint:

- Verification scenario matrix for NutShell Cache core paths.
- Zero-dependency Python evidence model and CLI.
- AI-human intervention log, written as audit evidence rather than decoration.
- Fault-injection plan for replacement, dirty bit, refill, write mask, and stall bugs.
- Initial report generator for competition submission materials.
- Executable Python harness smoke run: 48 transactions, 10/12 planned coverpoints
  covered, and dirty-writeback fault injection detected.

The RTL regression is not claimed as complete in this checkpoint. Measured
functional coverage will be reported after the Picker/Toffee loop is connected.

## Why This Project Should Score Well

| Competition dimension | CacheSage-UC response |
| --- | --- |
| Completeness | Covers read/write hits, misses, refill, dirty eviction, replacement pressure, stalls, reset recovery, boundary addresses, and long random streams. |
| Technical depth | Uses a reference memory model, event-order scoreboard obligations, constrained random knobs, and fault-injection targets. |
| AI usage efficiency | Keeps an explicit AI defect and human correction log so the review can see where UCAgent helped and where engineering judgment took over. |
| Engineering quality | Apache-2.0, small package boundaries, standard-library tests, reproducible commands, and report artifacts under version control. |

## Quick Start

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m cachesage_uc.cli plan
python -m cachesage_uc.cli run --seed 11 --count 48 --output reports/sample-run-seed11.json
python scripts/generate_report.py --output reports/initial-verification-report.md
```

The project intentionally uses only the Python standard library for the current
tooling layer. This keeps the evidence package easy to run on a fresh machine.

## Repository Layout

```text
src/cachesage_uc/        Evidence model and CLI.
tests/                   Standard-library regression tests.
docs/                    Verification plan, scoreboard notes, AI-HIL notes, and fault-injection design.
examples/                Machine-readable sample evidence.
reports/                 Generated and curated competition reports.
scripts/                 Small command-line helpers.
```

## Verification Direction

The next implementation layer will bind the documented scenarios to a real
Picker/Toffee flow:

1. Export the target NutShell Cache RTL into a Python-drivable DUT.
2. Build Toffee driver, monitor, reference memory model, and scoreboard modules.
3. Replay the scenario matrix with deterministic seeds.
4. Feed uncovered points and failing seeds back into UCAgent prompt rounds.
5. Replace planned coverage in the report with measured functional coverage.

The current Python harness already includes a reference cache model, constrained
transaction generator, scoreboard comparison, coverage attribution, and a
dirty-writeback fault mode. It is intentionally small enough to review by hand,
because the contest gives real weight to human intervention and code audit.

## License

Apache License 2.0. See [LICENSE](LICENSE).

