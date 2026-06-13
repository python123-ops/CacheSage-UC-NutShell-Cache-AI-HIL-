# AI-HIL Collaboration Log

This project treats UCAgent as a verification co-pilot, not as an unchecked code
generator. The review trail below is part of the submission evidence.

## Working Rules

- AI drafts can propose plans, skeletons, prompts, and first-pass code.
- Human review must approve cache invariants, scoreboard behavior, and coverage
  claims.
- Any generated code that touches the scoreboard must be reviewed against a
  concrete transaction trace.
- Reports separate planned coverage from measured regression coverage.
- Machine-readable review records live in `ai_hil_log.jsonl`, with the
  human-facing catalog summarized in `docs/ai-defect-catalog.md`.

## Early Intervention Table

| Stage | AI draft issue | Human correction | Reason it matters |
| --- | --- | --- | --- |
| Test-plan drafting | Replacement was described as one generic case. | Split into clean eviction, dirty eviction, and same-set pressure. | These fail in different ways and need different observations. |
| Scoreboard design | Checker compared only final read data. | Added event-order obligation for writeback before refill install. | A cache can return correct final data while losing a dirty victim. |
| CRV constraints | Uniform random addresses were used for all streams. | Added same-set bias and retained a small full-range stream. | Replacement pressure is unlikely under naive randomness. |
| Failure triage | Prompt asked AI to directly fix any mismatch. | Human first classifies scoreboard bug, DUT bug, or stimulus bug. | Blind fixing hides the root cause and weakens report credibility. |
| Report wording | Generated text implied RTL coverage was already measured. | Reworded to planned coverage until the regression artifacts exist. | The competition rewards evidence, not inflated phrasing. |
| Upstream adapter | Generated wrapper assumed the RTL shape without checking the example project. | Locked Example-NutShellCache and added a layout inspector before the smoke step. | Real integration work starts from the upstream flow, not from an invented interface. |

## Prompt Pattern

The preferred prompt format for later UCAgent rounds is:

```text
Target: NutShell Cache, scenario <ID>.
Observed gap: <uncovered coverpoint or failing seed>.
Known invariant: <human-approved cache rule>.
Allowed change: <stimulus constraint | scoreboard check | documentation>.
Do not change: <reference model behavior unless the trace proves it is wrong>.
Return: patch summary, new seed, expected coverage effect, and risks.
```

This structure keeps the AI focused and leaves a reviewable trail for the
"AI defect and human correction" part of the competition report.
