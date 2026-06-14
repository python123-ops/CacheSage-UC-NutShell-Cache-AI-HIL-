# CacheSage-UC 验证记录

本记录对应 UCAgent NutShell Cache 方向的当前工程状态。文档把计划覆盖点、Python harness 实测结果、RTL/Toffee 环境记录分开描述，避免把尚未运行的 RTL 数据写成已经完成的结论。

## 证据边界

| 证据类别 | 当前状态 | 已记录数据 |
| --- | --- | --- |
| 计划功能覆盖点 | 已定义 | 23 个 coverpoint，覆盖 12 个场景 |
| Python harness 实测覆盖率 | 已测量 | seed 11、96 个 transaction，23/23 (100.00%) |
| RTL/Toffee 实测覆盖率 | 环境记录 | 本机依赖齐全并运行 Picker/Toffee smoke 后单独记录 |

## 可执行 Harness 快照

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` | 通过 | 96 个 transaction，100.00% coverpoint |

## 场景矩阵

| ID | 场景 | 验证意图 | 覆盖点 |
| --- | --- | --- | --- |
| S01 | 读写冒烟路径 | 确认 Python driver、monitor 和 scoreboard 能闭合一个基本 cache transaction loop。 | cp_read_hit, cp_write_hit_mask, cp_read_after_write |
| S02 | read miss 与 refill | 覆盖 miss 请求、refill 接收和重放响应顺序。 | cp_read_miss_refill, cp_refill_alignment |
| S03 | write miss allocate | 检查 write-allocate 行为和 miss 后的 byte mask 保持。 | cp_write_miss_allocate, cp_write_hit_mask, cp_mask_mix |
| S04 | dirty eviction integrity | 在 replacement 安装新 line 前捕获脏 victim 丢写回问题。 | cp_dirty_eviction, cp_writeback_observed, cp_refill_after_dirty_evict |
| S05 | clean eviction 静默性 | 确认 clean victim 不会产生 phantom writeback。 | cp_clean_eviction, cp_replacement_rotation |
| S06 | replacement 压力 | 持续同 set 冲突，直到 replacement policy 状态错误可见。 | cp_replacement_rotation, cp_same_set_pressure, cp_long_random |
| S07 | stall 与 back-pressure | 验证 request、refill 或 response channel stall 时元数据保持稳定。 | cp_stall_hold, cp_refill_alignment |
| S08 | reset recovery | 检查 reset 会取消 miss/refill 窗口中的瞬态 cache 活动。 | cp_reset_recovery, cp_read_miss_refill |
| S09 | 边界地址 aliasing | 防住 line offset、tag/index slicing 在边界地址上的错误。 | cp_boundary_address, cp_offset_word_access, cp_write_hit_mask |
| S10 | 长随机回归 | 用 coverage hole 和 scoreboard mismatch 驱动复盘。 | cp_long_random, cp_dirty_eviction, cp_stall_hold, cp_multi_set_traffic |
| S11 | mask 与 offset 矩阵 | 暴露 full-word traffic 容易掩盖的 byte-lane 错误。 | cp_partial_mask_low, cp_partial_mask_high, cp_full_line_mask, cp_mask_mix |
| S12 | 事件级 replacement 审计 | 即使架构读数据仍然匹配，也要捕获 replacement 状态漂移。 | cp_same_set_pressure, cp_writeback_observed, cp_refill_after_dirty_evict |

## 设计复盘与修正记录

| 阶段 | 草案摘要 | 复核修正 | 经验记录 |
| --- | --- | --- | --- |
| 测试计划草案 | 最初草案列出了 read/write hit 和 miss，但把 replacement 合并成单一泛化场景。 | 把 replacement 拆成 clean eviction、dirty eviction 和 same-set pressure 三类，并补上 scoreboard 观察点。 | 覆盖率要命名被保护的 cache invariant，而不只是列操作类别。 |
| Scoreboard 设计 | 草稿 checker 只比对最终 read data，忽略 writeback order。 | 补上 scoreboard 约束：victim writeback 必须发生在 refill installation 之前。 | Cache 正确性不仅看最终内存内容，也要看关键事件顺序。 |
| CRV 约束 | 第一版随机流使用均匀地址，很难快速打到 replacement pressure。 | 把地址生成偏向同一个 set，同时保留少量 full-range traffic。 | 有效覆盖来自成形随机和少量定向 invariant 的组合。 |
| 失败分诊 | 初版分诊记录倾向于直接按 waveform 摘要修补 mismatch。 | 调整为先区分 scoreboard bug、DUT bug 或 stimulus bug，再决定修正位置。 | 补丁只有建立在可信工程诊断上才有意义。 |
| 报告口径 | 初版报告把计划覆盖率写得像已经完成的 RTL 覆盖率。 | 改为分别记录 planned coverpoints、Python harness 数据和 RTL/Toffee 实测数据。 | 公开材料可以说明目标，但覆盖率证据必须可审计。 |

## 故障注入记录

| fault mode | 结果 | 首个失败摘要 |
| --- | --- | --- |
| `drop_dirty_writeback` | 预期失败 | memory mismatch at 0x0: expected 0xDEADBEEF, observed 0x00000000 |
| `ignore_write_mask` | 预期失败 | data mismatch at 0x0: expected 287493341, observed 2864434397 |
| `stuck_replacement` | 预期失败 | eviction sequence mismatch: expected [('miss', 96, ''), ('eviction', 32, 'clean'), ('refill', 96, ''), ('read', 96, 'replace-evict-b')], observed [('miss', 96, ''), ('eviction', 64, 'clean'), ('refill', 96, ''), ('read', 96, 'replace-evict-b')] |
| `refill_shift` | 预期失败 | data mismatch at 0x0: expected 287454020, observed 0 |
| `unstable_under_stall` | 预期失败 | data mismatch at 0x0: expected 3405691582, observed 3405691457 |

## 故障模型目录

- drop_dirty_writeback: dirty victim 在 replacement 前未写回
- ignore_write_mask: store hit 忽略 byte mask
- stuck_replacement: eviction 后 replacement pointer 不推进
- refill_shift: refill beat index 偏移一个 word
- unstable_under_stall: downstream ready 为低时 request metadata/data 发生变化

## 集成环境记录

当前仓库已经提供 Picker/Toffee 适配边界、上游 Example-NutShellCache 锁定信息和 smoke 脚本。若本机没有安装 Picker、Toffee、Toffee-Test 或 make，RTL smoke 会记录依赖状态，Python harness 回归仍可独立复现。本项目不声称已经发现真实 NutShell RTL bug；现有 fault artifact 用于证明 injected fault 可被 harness 和 scoreboard 检出。
