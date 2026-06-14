# 参赛交付核查清单

本清单把仓库材料和 UCAgent NutShell Cache 方向的交付状态对应起来，便于提交前逐项核对。

| 方向 | 仓库材料 | 当前记录 |
| --- | --- | --- |
| 场景覆盖 | `docs/verification-plan.md`、`reports/sample-run-seed11.json` | 12 个场景和 23 个 coverpoint 覆盖数据路径、控制路径、mask、replacement、stall、reset 和 CRV |
| 验证核心 | `src/cachesage_uc/verification.py`、`docs/scoreboard-design.md` | reference model、event scoreboard、确定性 fault mode 和 directed replay 已实现 |
| 集成边界 | `src/cachesage_uc/adapters/`、`scripts/run_nutshell_smoke.py` | 上游结构检查、Toffee-style request 映射和依赖状态记录已具备 |
| 复核证据 | `review_journal.jsonl`、`docs/review-catalog.md` | 草案问题、人工复核发现、修正方式和关联证据已记录 |
| 仓库卫生 | `tests/`、`pyproject.toml`、`upstream.lock.json`、Apache-2.0 license | 标准库测试、复现命令、锁定上游 commit 和无 vendored 第三方源码 |

## 集成环境记录

| 项目 | 记录方式 |
| --- | --- |
| 上游源码 | 通过 `scripts/fetch_upstream_example.py` 按 `upstream.lock.json` 拉取到 `third_party/Example-NutShellCache` |
| Picker/Toffee 依赖 | 由 `scripts/run_nutshell_smoke.py` 写入 JSON/Markdown 状态 |
| RTL/Toffee 覆盖率 | 与 Python harness 覆盖率分栏记录，不混作同一数据源 |
| waveform 或 transaction trace | fault artifact 先保存 JSON 摘要，RTL smoke 运行后再附加波形来源 |
| 复核记录 | 新增 prompt round 时继续写入 `review_journal.jsonl` |

## 非声明项

仓库不声称真实 NutShell RTL 存在 bug。当前 fault artifact 是 injected fault 检出证据，用于说明验证环境和 scoreboard 的有效性。
