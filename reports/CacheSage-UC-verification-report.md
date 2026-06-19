# CacheSage-UC：面向 NutShell Cache 的 UCAgent 辅助自动化验证报告

报告日期：2026-06-19

GitLink：https://gitlink.org.cn/python123/cachesage-uc

GitHub：github.com/python123-ops/CacheSage-UC

提交基线：仓库当前默认分支 HEAD

## 摘要

CacheSage-UC 面向 UCAgent NutShell Cache 赛题，构建了 Python 验证核心和真实 RTL 回归两条可复现路径。Python harness 在 seed 11 上达到 `23/23`；Toffee 驱动 Picker DUT 完成 421 条事务，RTL 功能覆盖率为 `34/36`，独立 Scoreboard 完成 `199` 次比较且无失败；Verilator 代码覆盖率为 `898/1454（61.00%）`。报告同时保留 5 类 injected fault 和 UCAgent 人工复核记录，不把故障注入结果写成真实 NutShell RTL 缺陷。

关键词：UCAgent；NutShell Cache；Scoreboard；约束随机；故障注入；覆盖率

## 赛题任务对照

| 任务要求 | 仓库证据 | 状态 |
| --- | --- | --- |
| 完整验证组件 | Generator、Scoreboard、Reference Model、Coverage、Fault Injection | 已形成 Python harness |
| 验证报告 | `reports/initial-verification-report.md` 与本 PDF | 已整理 |
| 约束细化 | 12 个场景、23 个 coverpoint、same-set pressure 与 mask matrix | 已实现 |
| 架构重构 | `src/cachesage_uc/adapters/` 对齐 Picker/Toffee 风格接口 | 已建立边界 |
| 真实 RTL 回归 | `integration/nutshell/`、`scripts/run_rtl_regression.py` | 34/36，94.44% |
| 人工复核 | `review_journal.jsonl`、`docs/ucagent-collaboration.md` | 10 条可追溯记录 |
| 故障注入 | 5 类 injected fault artifact | 已检出 |

## 覆盖率与事件摘要

- Python harness 覆盖率：`23/23`，`100.00%`。
- RTL 功能覆盖率：`34/36`，`94.44%`；421 条真实 DUT 事务。
- RTL Scoreboard：`199` 次比较，`0` 个失败。
- 执行规模：seed 11，96 个 transaction。
- 事件计数：dirty_eviction=33, eviction=51, hit=41, masked_write=24, miss=55, read=50, refill=55, reset_window=1, stall_hold=2, write=46, writeback=33。
- Picker/Toffee/NutShell smoke：Linux 环境已完成上游 `make gen_dut` 与 `make test` smoke；已收集 7 个 RTL artifact manifest，包含 waveform 1 个、coverage candidate 2 个、generated DUT 4 个；Verilator RTL code coverage 898/1454 (61.00%)。
- RTL artifact manifest：已收集 7 个 RTL artifact manifest，包含 waveform 1 个、coverage candidate 2 个、generated DUT 4 个。
- RTL code coverage：Verilator RTL code coverage 898/1454 (61.00%)。

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
| RV-001 | 替换策略和 dirty victim 没有被单独拆开。 | 增加定向替换序列，并让 scoreboard 比较 writeback 事件。 | 3 类基本场景 -> 新增 dirty/clean evict… |
| RV-002 | 均匀分布难以快速命中同 set 冲突。 | 加入 same-set、word offset、mask mix 和多 set 约束。 | 随机流不保证 replacement pressure -> … |
| RV-003 | 缺少控制路径、替换策略和时序保持风险。 | 增加 stuck_replacement、refill_shift、unstable_under_stall，并固定 detecting seed。 | 2 类 fault -> 5 类 deterministic … |
| RV-004 | 计划覆盖点、Python 实测与 RTL 实测口径混在一起。 | 报告拆分证据类别，并明确 injected fault 不代表真实 RTL bug。 | 覆盖数据来源未分栏 -> 四类证据分别记录 |
| RV-005 | 没有读取上游工程结构就定义接口。 | 增加 fetch 脚本、layout inspector 和固定 commit。 | 接口来源不可复核 -> 上游 commit 与接入边界可复现 |
| RV-006 | 真实 NutShell Cache 是 64-bit data、8-bit mask、64-byte line、128 sets、4 ways；现有模型是 32-bit、16-byte line、2 sets、2 ways。 | 新增 RtlTransaction、RtlCacheConfig 和 0x2000 same-set stride，不修改快速 Python harness。 | RTL 参数未对齐 -> 64-bit/8-mask/64-b… |
| RV-007 | 上游 test_smoke 与 Python harness 是并行运行，自研事务没有驱动真实 DUT。 | 定义 36 个真实可观测点和 33/36 门槛，Scoreboard 有失败时禁止 complete。 | RTL functional coverage 未导出 -> … |
| RV-008 | 没有观察 victim_way_mask，也没有驱动 io_out_coh probe。 | 将替换、一致性和协议恢复纳入真实 DUT directed spine 与覆盖结果。 | 上游 smoke 1 case -> 真实 DUT 覆盖 34… |
| RV-009 | 上游 non_block_write 以位置参数构造 ReqMsg，64 位 data 被传入 size，实际 data 保持为 0；参考模型复用同一调用路径，因此没有独立检出。 | 新增 NutShellRequestDriver，直接调用 send_req(address, size, cmd, mask, data)，同时增加真实 DUT write-read smoke。 | 上游 convenience driver 写后读回 0，参考… |
| RV-010 | 真实 RTL 在数据 Cache 实例上触发 only allow to flush icache 断言，说明该激励违反当前 DUT 约束。 | 将 rtl_flush_empty 替换为 rtl_idle_empty，并用真实 io_empty 信号命中。 | 三 seed 完成后因非法 flush 触发 RTL fata… |

## 集成边界

Linux 环境依赖齐全；上游 make gen_dut 与 make test smoke 已通过。

Python harness `23/23`、RTL 功能覆盖 `34/36` 和 RTL 代码覆盖 `898/1454` 分别记录，不互相替代。

本报告将 Python harness 结果与 RTL/Toffee 结果分开记录。上述 fault artifact 仅说明 injected fault 能被 harness 和 scoreboard 检出，不代表真实 NutShell RTL 存在对应缺陷。
