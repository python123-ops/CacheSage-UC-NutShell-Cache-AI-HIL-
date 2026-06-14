# CacheSage-UC NutShell Smoke 记录

- 状态：`rtl_smoke_complete`
- 上游目录：`third_party/Example-NutShellCache`
- 缺失路径：无
- Python harness：通过，23/23 个 coverpoint
- `make gen_dut`: exit 0
- `make test`: exit 0
- RTL artifact manifest：collected，记录 7 个候选产物
  - `third_party/Example-NutShellCache/Cache/VCache_coverage.dat` (coverage_candidate, 3573276 bytes)
  - `third_party/Example-NutShellCache/VCache_coverage.dat` (coverage_candidate, 3573739 bytes)
  - `third_party/Example-NutShellCache/Cache/Makefile` (generated_dut, 2807 bytes)
  - `third_party/Example-NutShellCache/Cache/dut_type.hpp` (generated_dut, 1612 bytes)
  - `third_party/Example-NutShellCache/Cache/example.py` (generated_dut, 232 bytes)
- RTL code coverage：exported，{'lines_found': 1454, 'lines_hit': 1162, 'functions_found': 0, 'functions_hit': 0, 'branches_found': 0, 'branches_hit': 0, 'line_percent': 79.92, 'function_percent': None, 'branch_percent': None}
- 记录说明：RTL artifact 与 code coverage 只作为 smoke-level 证据；Python harness functional coverage 仍单独记录。
