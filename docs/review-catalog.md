# 复核记录目录

本目录记录已经改变验证计划或 testbench 实现的复核发现。

| ID | 复核发现 | 修正方式 | 关联证据 |
| --- | --- | --- | --- |
| RV-001 | replacement 被当成一个泛化场景 | 拆分 clean eviction、dirty eviction 和 same-set pressure | `docs/verification-plan.md`、`tests/test_verification_core.py` |
| RV-002 | 草案建议均匀随机地址 | 在随机尾段前加入 directed coverage spine | `build_seeded_random_sequence(seed=11,count=96)` |
| RV-003 | fault injection 只覆盖 dirty writeback 和 mask | 增加 `stuck_replacement`、`refill_shift`、`unstable_under_stall` | `test_each_fault_mode_has_a_deterministic_detecting_sequence` |
| RV-004 | 报告口径混淆计划覆盖点和 RTL 实测覆盖率 | 拆成 planned、Python harness 和 RTL/Toffee 三类证据 | `reports/initial-verification-report.md` |
| RV-005 | adapter 设计在读上游结构前先猜接口 | 锁定 Example-NutShellCache commit，并在 smoke 前检查 layout | `upstream.lock.json`、`docs/upstream-survey.md` |
| RV-006 | Python harness 参数与真实 DUT 宽度、行和组数不一致 | 建立独立 RTL 事务与配置模型 | `src/cachesage_uc/rtl_verification.py` |
| RV-007 | 上游 smoke 不能代表自研场景的 RTL 功能覆盖率 | 建立 36 点真实 DUT 覆盖收集器 | `reports/rtl-functional-coverage.json` |
| RV-008 | 简单 read/write 没有观察替换和一致性 | 采集 memory、victim 和 coherence 事件 | `integration/nutshell/test_rtl_regression.py` |
| RV-009 | 上游写请求位置参数错位且同源参考模型未报警 | 使用显式协议字段驱动和独立 Scoreboard | `src/cachesage_uc/adapters/nutshell_runtime.py` |
| RV-010 | 通用 flush 假设违反当前 DCache 约束 | 改为观察合法的 `io_empty` 空闲恢复 | `src/cachesage_uc/rtl_coverage.py` |

`review_journal.jsonl` 是机器可读来源，测试和报告复核都会读取它。

完整的草案、人工发现、风险、代码修正和指标变化见 `docs/ucagent-collaboration.md`。
