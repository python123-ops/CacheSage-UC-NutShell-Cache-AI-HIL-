# 参赛交付核查清单

本清单把仓库材料和 UCAgent NutShell Cache 方向的交付状态对应起来，便于提交前逐项核对。

| 方向 | 仓库材料 | 当前记录 |
| --- | --- | --- |
| 场景覆盖 | `docs/verification-plan.md`、`reports/sample-run-seed11.json` | 12 个场景和 23 个 coverpoint 覆盖数据路径、控制路径、mask、replacement、stall、reset 和 CRV |
| 验证核心 | `src/cachesage_uc/verification.py`、`docs/scoreboard-design.md` | reference model、event scoreboard、确定性 fault mode 和 directed replay 已实现 |
| RTL 功能覆盖 | `integration/nutshell/`、`reports/rtl-functional-coverage.json` | 421 条真实 DUT 事务，`34/36（94.44%）`，199 次 Scoreboard 比较、0 失败 |
| RTL 代码覆盖 | `scripts/run_rtl_regression.py` | Verilator `898/1454（61.00%）`，与功能覆盖率分栏记录 |
| 复核证据 | `review_journal.jsonl`、`docs/ucagent-collaboration.md` | 草案、人工发现、代码修正、指标变化、命令、产物和提交均已记录 |
| 仓库卫生 | `tests/`、`pyproject.toml`、`upstream.lock.json`、Apache-2.0 license | 标准库测试、复现命令、锁定上游 commit 和无 vendored 第三方源码 |

## 集成环境记录

| 项目 | 记录方式 |
| --- | --- |
| 上游源码 | 通过 `scripts/fetch_upstream_example.py` 按 `upstream.lock.json` 拉取到 `third_party/Example-NutShellCache` |
| Picker/Toffee 依赖 | 由 `scripts/run_nutshell_smoke.py` 写入 JSON/Markdown 状态 |
| RTL smoke artifact | 记录 waveform、generated DUT、coverage candidate manifest，不提交大型二进制 |
| RTL 功能覆盖率 | `reports/rtl-functional-coverage.json` 保存逐覆盖点命中次数和真实事件来源 |
| RTL 代码覆盖率 | `coverage.dat` 已解析为 `898/1454（61.00%）` |
| waveform 或 transaction trace | 本地 FST 为 219100 bytes；仓库提交 manifest 和摘要，不提交大型二进制 |
| 复核记录 | RV-001 至 RV-010 记录于 `review_journal.jsonl`，其中重建记录与同步记录明确区分 |

## 非声明项

仓库不声称真实 NutShell RTL 存在 bug。当前 fault artifact 是 injected fault 检出证据，用于说明验证环境和 scoreboard 的有效性。
