# Submission Checklist Against The UCAgent Track

This checklist is written for the reviewer and for future maintenance. It maps
the repository artifacts to the public scoring dimensions of the UCAgent
NutShell Cache track.

| Scoring dimension | Weight | Current artifact | Status |
| --- | ---: | --- | --- |
| Completeness | 40% | `docs/verification-plan.md`, `reports/sample-run-seed11.json` | Core cache paths planned and executable harness covers 10/12 planned points. |
| Technical depth | 30% | `src/cachesage_uc/verification.py`, `docs/scoreboard-design.md` | Reference model, scoreboard, CRV stream, replacement stress, and dirty-writeback fault mode are implemented. |
| AI usage efficiency | 20% | `docs/ai-human-collaboration.md`, report AI correction table | AI output is treated as draft material; human corrections are recorded as review evidence. |
| Engineering quality | 10% | `tests/`, `pyproject.toml`, Apache-2.0 license, generated reports | Standard-library tests, reproducible commands, structured docs, and no hidden dependency chain. |

## First-Prize Direction

The current repository is stronger than a plain README submission because it has
an executable verification core. To reach a first-prize-level final submission,
the remaining work should be:

1. attach the harness to the actual Picker-exported NutShell Cache DUT;
2. replace planned coverage with measured RTL functional coverage;
3. keep the dirty-writeback fault as a regression sanity check;
4. add waveform or transaction-trace snippets for at least one detected injected fault;
5. expand the AI-HIL log with real prompts from UCAgent sessions, including one
   rejected generated patch and the human reason for rejection.

## Non-Claims

The repository does not yet claim that NutShell RTL has a real bug. The current
fault artifacts are injected-fault checks used to prove the verification
environment can detect meaningful cache mistakes.
