# 故障注入方案

故障注入用于确认验证环境能抓住常见 cache 错误。这里的 fault mode 是 testbench 自带的 injected fault，不代表真实 NutShell RTL 存在对应缺陷。

| fault mode | 注入行为 | 预期检测器 | 确定性入口 |
| --- | --- | --- | --- |
| `drop_dirty_writeback` | dirty victim 在 replacement 前没有写回 | final memory mismatch 与缺失 writeback event | `build_fault_sequence(FaultMode.DROP_DIRTY_WRITEBACK)` |
| `ignore_write_mask` | store hit 忽略 byte mask 并覆盖所有 byte lane | 未选中字节 readback mismatch | `build_fault_sequence(FaultMode.IGNORE_WRITE_MASK)` |
| `stuck_replacement` | same-set pressure 下 replacement pointer 不推进 | event-level scoreboard 观察到错误 eviction address | `build_fault_sequence(FaultMode.STUCK_REPLACEMENT)` |
| `refill_shift` | refill data 偏移一个 word | dirty line eviction/refill 后 readback mismatch | `build_fault_sequence(FaultMode.REFILL_SHIFT)` |
| `unstable_under_stall` | stall-tagged request 被 hold 时 data 发生变化 | readback mismatch 与 `unstable_under_stall` event | `build_fault_sequence(FaultMode.UNSTABLE_UNDER_STALL)` |

## 接收规则

每个 injected fault 至少有一条确定性 sequence，并且失败原因要与 fault 类型匹配。有效 artifact 至少包含：

- fault mode 与 deterministic seed 或 directed sequence 名称；
- transaction trace 摘要；
- 首个 scoreboard 或 monitor failure；
- 失败路径触达的 coverpoint；
- 人工诊断记录，再进入修正建议环节。

当前可执行证据：

- `tests/test_verification_core.py::test_each_fault_mode_has_a_deterministic_detecting_sequence` 覆盖五类 fault mode。
- `reports/fault-drop-dirty-writeback.json` 记录 dirty victim loss 样例。
- 报告生成器输出 fault matrix，并明确不把 injected fault 写成真实 RTL bug。
