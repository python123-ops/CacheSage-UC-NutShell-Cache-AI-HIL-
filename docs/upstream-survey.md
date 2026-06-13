# Upstream Survey: XS-MLVP/Example-NutShellCache

Survey date: 2026-06-14  
Pinned commit: `cdc9ef7d4dfc3d8fbd969869f6696afe27cfed2a`  
Repository: https://github.com/XS-MLVP/Example-NutShellCache

## Observed Repository Shape

The upstream example is the closest public alignment target for this project.
The root entries observed at the pinned commit are:

| Path | Role in CacheSage-UC |
| --- | --- |
| `Makefile` | Provides the expected `gen_dut`, `test`, and `clean` flow shape. |
| `rtl/` | Verilog RTL source area consumed by Picker. |
| `src/` | Python-side testbench/support code in the upstream example. |
| `test/` | Upstream tests and example regression entry points. |
| `pytest.ini` | Confirms the example is intended to be exercised from Python tests. |
| `Readme.md` | Documents Picker, Toffee, and Toffee-Test requirements. |
| `nutshell_cache_report_demo.pdf` | Upstream demonstration report, useful as a style reference only. |

## Why We Do Not Vendor It

The competition repo should stay focused and reviewable. CacheSage-UC therefore
stores only `upstream.lock.json` plus a fetch script. This gives repeatability
without copying a large third-party tree into the submission.

```powershell
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
```

## Adapter Boundary

`src/cachesage_uc/adapters/nutshell_example.py` checks whether the fetched tree
contains the required paths. `src/cachesage_uc/adapters/toffee_bridge.py` maps
the current `Transaction` object into a Toffee-style cache request case:

- `op`: `read` or `write`;
- `addr`: byte address;
- `data`: 32-bit write data;
- `mask`: byte mask;
- `meta.tag`: deterministic trace label used by the scoreboard.

This lets the Python harness and the later Toffee DUT path share the same seed,
trace labels, and coverage vocabulary.
