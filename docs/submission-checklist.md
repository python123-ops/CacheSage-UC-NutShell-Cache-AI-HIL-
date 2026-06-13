# Submission Checklist Against The UCAgent Track

This checklist maps the repository artifacts to the public scoring dimensions
of the UCAgent NutShell Cache track.

| Scoring dimension | Weight | Current artifact | Status |
| --- | ---: | --- | --- |
| Completeness | 40% | `docs/verification-plan.md`, `reports/sample-run-seed11.json` | 12 scenarios and 23 coverpoints cover cache data, control, mask, replacement, stall, reset, and CRV paths. |
| Technical depth | 30% | `src/cachesage_uc/verification.py`, `src/cachesage_uc/adapters/`, `docs/scoreboard-design.md` | Reference model, event scoreboard, deterministic fault modes, upstream layout inspection, and Toffee case mapping are implemented. |
| AI usage efficiency | 20% | `ai_hil_log.jsonl`, `docs/ai-defect-catalog.md`, report AI correction table | AI output is treated as draft material; human corrections are recorded as review evidence with linked tests/docs. |
| Engineering quality | 10% | `tests/`, `pyproject.toml`, `upstream.lock.json`, Apache-2.0 license | Standard-library tests, reproducible commands, locked upstream commit, no vendored third-party source, and clear no-dependency fallback. |

## First-Prize Direction

The repository is no longer only a plan. It has an executable harness and an
adapter boundary for Example-NutShellCache. The next high-value checkpoints are:

1. run `scripts/fetch_upstream_example.py` and install Picker/Toffee locally;
2. invoke upstream `make gen_dut` and bind the generated Python DUT into the
   CacheSage driver/monitor path;
3. add RTL/Toffee measured functional coverage next to the Python harness result;
4. attach waveform or transaction-trace snippets for at least one injected fault;
5. keep extending `ai_hil_log.jsonl` with real prompt rounds and human rejection reasons.

## Non-Claims

The repository does not claim that NutShell RTL has a real bug. The current
fault artifacts are injected-fault checks used to prove the verification
environment can detect meaningful cache mistakes.
