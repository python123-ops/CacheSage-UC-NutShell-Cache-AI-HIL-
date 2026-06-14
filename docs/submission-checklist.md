# Submission Readiness Checklist

This checklist maps the repository artifacts to the expected handoff state for
the UCAgent NutShell Cache track.

| Area | Current artifact | Status |
| --- | --- | --- |
| Scenario coverage | `docs/verification-plan.md`, `reports/sample-run-seed11.json` | 12 scenarios and 23 coverpoints cover cache data, control, mask, replacement, stall, reset, and CRV paths. |
| Verification core | `src/cachesage_uc/verification.py`, `docs/scoreboard-design.md` | Reference model, event scoreboard, deterministic fault modes, and directed replay are implemented. |
| Integration boundary | `src/cachesage_uc/adapters/`, `scripts/run_nutshell_smoke.py` | Upstream layout inspection, Toffee-style request mapping, and dependency-aware smoke output are present. |
| Review trail | `review_journal.jsonl`, `docs/review-catalog.md` | Draft issues and human corrections are recorded with linked tests/docs. |
| Repository hygiene | `tests/`, `pyproject.toml`, `upstream.lock.json`, Apache-2.0 license | Standard-library tests, reproducible commands, locked upstream commit, and no vendored third-party source. |

## Remaining Integration Work

1. run `scripts/fetch_upstream_example.py` and install Picker/Toffee locally;
2. invoke upstream `make gen_dut` and bind the generated Python DUT into the
   CacheSage driver/monitor path;
3. add RTL/Toffee measured functional coverage next to the Python harness result;
4. attach waveform or transaction-trace snippets for at least one injected fault;
5. keep extending `review_journal.jsonl` with real prompt rounds and human review notes.

## Non-Claims

The repository does not claim that NutShell RTL has a real bug. The current
fault artifacts are injected-fault checks used to validate the verification
environment.
