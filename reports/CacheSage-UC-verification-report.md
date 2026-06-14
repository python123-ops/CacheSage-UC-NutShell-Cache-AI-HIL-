# CacheSage-UC：面向 NutShell Cache 的 UCAgent 辅助自动化验证报告

报告日期：2026-06-14  
GitLink：https://gitlink.org.cn/python123/cachesage-uc  
GitHub：github.com/python123-ops/CacheSage-UC  
提交基线：仓库当前默认分支 HEAD

## 摘要

CacheSage-UC 面向 UCAgent NutShell Cache 赛题，构建了一套可复现的 cache 验证原型。当前证据包括 Python harness、Generator/CRV、Scoreboard、Coverage、5 类 injected fault、人工复核记录，以及 Linux 环境下的 Picker/Toffee/NutShell smoke。Python harness 在 seed 11、96 个 transaction 上达到 `23/23`，即 `100.00%` 覆盖率。报告仍将 smoke 通过与 RTL measured coverage 分开记录，不声称已发现真实 NutShell RTL bug。

关键词：UCAgent；NutShell Cache；Scoreboard；约束随机；故障注入；覆盖率

## 赛题任务对照

| 任务要求 | 仓库证据 | 状态 |
| --- | --- | --- |
| 完整验证组件 | Generator、Scoreboard、Reference Model、Coverage、Fault Injection | 已形成 Python harness |
| 验证报告 | `reports/initial-verification-report.md` 与本 PDF | 已整理 |
| 约束细化 | 12 个场景、23 个 coverpoint、same-set pressure 与 mask matrix | 已实现 |
| 架构重构 | `src/cachesage_uc/adapters/` 对齐 Picker/Toffee 风格接口 | 已建立边界 |
| 故障注入 | 5 类 injected fault artifact | 已检出 |

## 覆盖率与事件摘要

- Python harness 覆盖率：`23/23`，`100.00%`。
- 执行规模：seed 11，96 个 transaction。
- 事件计数：dirty_eviction=33, eviction=51, hit=41, masked_write=24, miss=55, read=50, refill=55, reset_window=1, stall_hold=2, write=46, writeback=33。
- Picker/Toffee/NutShell smoke：Linux 环境已完成上游 `make gen_dut` 与 `make test` smoke；RTL/Toffee measured coverage 尚未由上游测试导出。

## 故障注入记录

| fault mode | 检出结果 | failure 数 | 首个失败摘要 |
| --- | --- | --- | --- |
| `drop_dirty_writeback` | 预期失败 | 6 | memory mismatch at 0x0: expected 0x01020304, observed 0x00000000 |
| `ignore_write_mask` | 预期失败 | 4 | memory mismatch at 0x4: expected 0x0000CCDD, observed 0xAABBCCDD |
| `refill_shift` | 预期失败 | 13 | memory mismatch at 0xC: expected 0x00000000, observed 0x11223344 |
| `stuck_replacement` | 预期失败 | 6 | memory mismatch at 0x20: expected 0x55667788, observed 0x00000000 |
| `unstable_under_stall` | 预期失败 | 2 | data mismatch at 0x0: expected 3405691582, observed 3405691457 |

## 人工复核记录

| ID | 复核发现 | 修正方式 | 覆盖率变化 |
| --- | --- | --- | --- |
| RV-001 | 替换策略和 dirty victim 没有被单独拆开，容易把最关键的数据一致性问题藏在随机流里。 | 补入 directed dirty eviction、clean eviction、same-set pressure，并让 scoreboard 检查 writeback 事件。 | 新增替换与脏写回覆盖 |
| RV-002 | 均匀分布很难快速打到同 set 冲突，也不利于复现 replacement failure。 | 将 seed 前缀做成 directed coverage spine，随机段再混入 word offset、mask 和多 set 访问。 | 新增 same-set、mask、offset 覆盖 |
| RV-003 | 这会让作品看起来像普通脚本，缺少 cache 控制路径和时序保持类风险。 | 补充 stuck_replacement、refill_shift、unstable_under_stall，并为每个 fault 固定 deterministic seed。 | fault mode 从 2 类扩展到 5 类 |
| RV-004 | 这个口径会在评审追问 Toffee 证据时露怯。 | 报告拆成 planned coverage、Python harness measured coverage、RTL/Toffee measured coverage 三栏，真实 RTL 暂不夸大。 | 报告证据分栏 |
| RV-005 | 没有读取上游工程结构就定义接口，后续很可能与 Picker/Toffee 真实路径对不上。 | 锁定 XS-MLVP/Example-NutShellCache commit，新增 fetch 脚本和 layout inspector，只在本地拉取第三方源码。 | 集成边界可复现 |

## 集成边界

Linux 环境依赖齐全；上游 make gen_dut 与 make test smoke 已通过。

本报告将 Python harness 结果与 RTL/Toffee 结果分开记录。上述 fault artifact 仅说明 injected fault 能被 harness 和 scoreboard 检出，不代表真实 NutShell RTL 存在对应缺陷。
