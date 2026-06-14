# CacheSage-UC

CacheSage-UC 面向 UCAgent NutShell Cache 验证任务，目标是把 cache 验证从“随机跑一批读写”推进到可复盘的工程流程：场景先写清楚，事务能复现，scoreboard 有明确不变量，报告把 Python harness 数据和 RTL/Toffee 数据分开记录。

当前仓库包含可运行的 Python 验证核心、23 个功能覆盖点、5 类确定性故障注入、NutShell 上游示例工程锁定脚本、Picker/Toffee 适配边界，以及人工复核记录。项目不声称已经发现真实 NutShell RTL bug；现有 fault artifact 用于证明 injected fault 能被 harness 和 scoreboard 检出。

## 当前交付状态

| 层次 | 状态 | 证据 |
| --- | --- | --- |
| Python 验证核心 | 可运行 | `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` |
| 功能覆盖模型 | 23 个 coverpoint | read/write hit、refill、dirty/clean eviction、mask、stall、reset、same-set pressure |
| 故障注入 | 5 个确定性模式 | `drop_dirty_writeback`、`ignore_write_mask`、`stuck_replacement`、`refill_shift`、`unstable_under_stall` |
| NutShell 上游对齐 | 锁定版本，不 vendoring | `upstream.lock.json`、`scripts/fetch_upstream_example.py` |
| Picker/Toffee 边界 | 已有适配层 | `src/cachesage_uc/adapters/`、`scripts/run_nutshell_smoke.py` |
| RTL/Toffee 实测覆盖率 | 单独记录 | 本机依赖齐全并运行 smoke 后写入，不与 Python harness 覆盖率混写 |

## 验证能力

| 方向 | 当前实现 |
| --- | --- |
| cache 数据路径 | read/write hit、miss/refill、write-allocate、byte mask、dirty 与 clean eviction |
| 控制路径压力 | same-set pressure、replacement rotation、stall window、reset recovery、boundary offset |
| Scoreboard | 比对 read data、最终 backing memory、writeback/refill/stall 等事件签名 |
| 复核证据 | `review_journal.jsonl` 和 `docs/review-catalog.md` 记录草案问题、复核发现和修正方式 |
| 集成边界 | 检查上游 Example-NutShellCache 结构，并把事务流映射成 Toffee-style request case |

## 复现命令

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
python -m cachesage_uc.cli plan
python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json
python scripts/generate_report.py --output reports/initial-verification-report.md
```

基础验证层只使用 Python 标准库。Picker、Toffee、Toffee-Test 和 make 只用于 RTL smoke 路径。

## NutShell / Toffee 环境说明

```powershell
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache --dry-run
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
```

如果本机没有上游目录或缺少 Picker/Toffee 相关依赖，`run_nutshell_smoke.py` 会写出 machine-readable 状态文件，并保持 Python harness 回归可独立复现。

## 仓库结构

```text
src/cachesage_uc/        验证核心、证据模型、CLI 和适配层
tests/                   标准库 unittest 回归
docs/                    验证计划、上游调研、Toffee 流程、复核记录
examples/                机器可读样例证据
reports/                 生成记录和样例验证结果
scripts/                 报告生成、上游拉取和 smoke helper
review_journal.jsonl     prompt / draft / review correction 记录
upstream.lock.json       Example-NutShellCache 固定来源信息
```

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
