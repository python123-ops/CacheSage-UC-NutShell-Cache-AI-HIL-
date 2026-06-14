# Scoreboard 设计记录

Scoreboard 是本项目最需要人工复核的部分。Cache bug 经常不是“立即读错数据”这么简单，而是事件顺序错误：dirty victim 写回太晚、refill 覆盖活跃 line，或者 stall 时 request metadata 漂移，但短路径 readback 看起来仍然正常。

## 当前可执行 Harness

当前 Python harness 刻意保持小而可审阅：

- `Transaction` 表示对齐 read/write 操作和 byte mask。
- `CacheModel` 是带 dirty bit、refill、replacement、writeback 和 fault mode 的 set-associative cache。
- `VerificationRunner` 用同一序列分别驱动 golden model 和 candidate model，再比较 read response、最终 backing memory 和 monitor event signature。
- 覆盖率来自实际观测到的 transaction 和 cache event，而不是只靠手写 checklist。

这不是最终 Picker/Toffee DUT binding 的替代品，而是 scoreboard rehearsal：在 RTL adapter 接上之前，先让规则可执行、可复查。

## 人工复核的不变量

| invariant | 重要性 | 当前检测方式 |
| --- | --- | --- |
| masked write 保留未选中字节 | store 在选中字节正确时仍可能污染邻近 byte lane | 对 reference memory 做 readback 比对 |
| dirty victim writeback 先于 replacement 完成 | end-state data 可能在 refill 成功后仍丢失 | final memory comparison 与 writeback event coverage |
| replacement 在 same-set pressure 下轮转 | 普通随机流不一定触发 replacement state bug | same-set constrained stream 与 eviction-address event comparison |
| refill event 对齐目标 line | beat indexing bug 常在 line offset 下出现 | refill event 与 readback coverage |
| stall window 保持 metadata/data 稳定 | 短 architectural readback 可能漏掉 handshake stability bug | stall-tagged transaction 与 event-level scoreboard failure |
| failure 先分类再修补 | 直接 patch 容易掩盖 scoreboard 或 stimulus bug | review journal 与 fault JSON artifact |

## Toffee 映射方式

Python harness 与 Toffee 组件的对应关系：

- `Transaction` 对应 generator item。
- `CacheModel` 对应 reference model。
- cache event 对应 request、response、refill、writeback channel 上的 monitor observation。
- `VerificationRunner` 对应 regression wrapper，负责保存 seed、coverage 和 failure artifact。

RTL 路径沿用同一条规则：没有 scoreboard 或 monitor 观察支撑的 coverpoint 不计入覆盖。
