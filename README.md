# CacheSage-UC

CacheSage-UC 面向 UCAgent NutShell Cache 验证任务，目标是把 cache 验证从“随机跑一批读写”推进到可复盘的工程流程：场景先写清楚，事务能复现，Scoreboard 有明确不变量，报告把 Python harness、RTL 功能覆盖率和 RTL 代码覆盖率分开记录。

当前仓库包含可运行的 Python 验证核心、真实 NutShell Cache 的 Toffee 回归、两套独立覆盖模型、5 类确定性故障注入，以及可追溯的人工复核记录。项目不把 injected fault 写成真实 NutShell RTL 缺陷；本轮真实 DUT 回归的 199 次读数据比较均通过。

## 当前交付状态

| 层次 | 状态 | 证据 |
| --- | --- | --- |
| Python 验证核心 | 可运行 | `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` |
| Python 功能覆盖率 | `23/23（100%）` | `reports/sample-run-seed11.json` |
| 故障注入 | 5 个确定性模式 | `drop_dirty_writeback`、`ignore_write_mask`、`stuck_replacement`、`refill_shift`、`unstable_under_stall` |
| NutShell 上游对齐 | 锁定版本，不 vendoring | `upstream.lock.json`、`scripts/fetch_upstream_example.py` |
| Picker/Toffee 回归 | Linux 实测通过 | 定向场景 + seed `11/29/73`，共 421 条真实 DUT 事务 |
| RTL 功能覆盖率 | `34/36（94.44%）` | `reports/rtl-functional-coverage.json`，199 次 Scoreboard 比较、0 失败 |
| RTL 代码覆盖率 | `898/1454（61.00%）` | Verilator `coverage.dat` 经 `verilator_coverage --annotate` 解析 |
| RTL 运行产物 | 本地保留 | FST 波形 219100 bytes，coverage.dat 3621619 bytes；仓库提交摘要，不提交大型二进制 |

## 验证能力

| 方向 | 当前实现 |
| --- | --- |
| cache 数据路径 | read/write hit、miss/refill、write-allocate、byte mask、dirty 与 clean eviction |
| 控制路径压力 | same-set pressure、replacement rotation、stall window、reset recovery、boundary offset |
| Scoreboard | 比对 read data、最终 backing memory、writeback/refill/stall 等事件签名 |
| 复核证据 | `review_journal.jsonl` 和 `docs/ucagent-collaboration.md` 记录草案、人工发现、代码修正、指标变化和关联提交 |
| 真实 RTL 集成 | 显式 SimpleBus 驱动，采集 DUT 响应、memory refill/writeback、victim way 和 coherence probe |

## 复现命令

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
python -m cachesage_uc.cli plan
python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json
python scripts/generate_report.py --output reports/initial-verification-report.md
```

基础验证层只使用 Python 标准库。真实 RTL 回归在 WSL Ubuntu 24.04 中使用 Picker、Toffee、Toffee-Test、Verilator 和 make。

## NutShell / Toffee 环境说明

```bash
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache --dry-run
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
python scripts/run_rtl_regression.py
```

如果本机没有上游目录或缺少 Picker/Toffee 相关依赖，`run_nutshell_smoke.py` 会写出 machine-readable 状态文件，并保持 Python harness 回归可独立复现。

## 仓库结构

```text
src/cachesage_uc/        Python 验证核心、RTL 事务模型、覆盖模型、CLI 和适配层
integration/nutshell/    真实 Picker DUT 的 Toffee smoke 与三 seed 回归
tests/                   标准库 unittest 回归
docs/                    验证计划、上游调研、Toffee 流程、复核记录
examples/                机器可读样例证据
reports/                 生成记录和样例验证结果
scripts/                 报告生成、上游拉取和 smoke helper
review_journal.jsonl     UCAgent 草案、人工复核、代码修正和指标记录
upstream.lock.json       Example-NutShellCache 固定来源信息
```

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
