# 复核记录目录

本目录记录已经改变验证计划或 testbench 实现的复核发现。

| ID | 复核发现 | 修正方式 | 关联证据 |
| --- | --- | --- | --- |
| RV-001 | replacement 被当成一个泛化场景 | 拆分 clean eviction、dirty eviction 和 same-set pressure | `docs/verification-plan.md`、`tests/test_verification_core.py` |
| RV-002 | 草案建议均匀随机地址 | 在随机尾段前加入 directed coverage spine | `build_seeded_random_sequence(seed=11,count=96)` |
| RV-003 | fault injection 只覆盖 dirty writeback 和 mask | 增加 `stuck_replacement`、`refill_shift`、`unstable_under_stall` | `test_each_fault_mode_has_a_deterministic_detecting_sequence` |
| RV-004 | 报告口径混淆计划覆盖点和 RTL 实测覆盖率 | 拆成 planned、Python harness 和 RTL/Toffee 三类证据 | `reports/initial-verification-report.md` |
| RV-005 | adapter 设计在读上游结构前先猜接口 | 锁定 Example-NutShellCache commit，并在 smoke 前检查 layout | `upstream.lock.json`、`docs/upstream-survey.md` |

`review_journal.jsonl` 是机器可读来源，测试和报告复核都会读取它。
