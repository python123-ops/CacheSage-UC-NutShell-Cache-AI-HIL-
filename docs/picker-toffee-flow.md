# Picker / Toffee Flow

This document records the intended execution path from the current Python
harness to the real NutShell Cache RTL flow.

## Local Preparation

```powershell
python -m pip install -e .
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
```

Install Picker, Toffee, and Toffee-Test following the upstream project guidance:

- https://github.com/XS-MLVP/picker
- https://github.com/XS-MLVP/toffee
- https://github.com/XS-MLVP/toffee-test

## Expected Upstream Commands

Inside the fetched upstream tree:

```powershell
make gen_dut
make test
make clean
```

CacheSage-UC does not assume the RTL interface blindly. The adapter first checks
the expected upstream structure, then maps the existing transaction stream into
Toffee-style request cases.

## CacheSage Smoke Boundary

```powershell
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
```

When the upstream tree is missing, the script returns exit code `2`, writes a
JSON status file, and prints the exact fetch command. When the tree is present,
the script writes:

- inspected upstream layout;
- Python harness result for seed 11, count 96;
- a preview of Toffee-style request cases;
- `rtl_toffee_measured_coverage: null` until a generated DUT run is attached.

## Coverage Reporting Contract

CacheSage-UC keeps three buckets separate:

| Bucket | Meaning |
| --- | --- |
| Planned coverage | The functional coverpoints in `docs/verification-plan.md`. |
| Python harness measured coverage | What `VerificationRunner` measured on the reference/candidate cache model. |
| RTL/Toffee measured coverage | What the Picker-generated DUT run measured; this remains empty until the dependency flow is actually run. |

This is intentionally conservative: the integration record should show measured
results, not overstate the current state.
