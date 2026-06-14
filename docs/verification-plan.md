# CacheSage-UC 验证计划

本文档记录 NutShell Cache 目标的工作验证计划。重点不是把读写事务随机堆大，而是把 cache 行为、不变量、观测点和可复现命令写清楚。

## 范围说明

- Picker 用于把 RTL 暴露为 Python 可驱动的 DUT。
- Toffee 组织 driver、monitor、reference model、scoreboard 和 coverage。
- UCAgent 用于草案生成、coverage hole 分析和 failing seed 解释。
- 人工复核负责确认 cache invariant、scoreboard 规则和报告口径。

本计划不扩展到未暴露接口的多核一致性场景。当前优先级放在 replacement、dirty eviction、byte mask、stall stability 和 reset recovery 上，因为这些路径容易被浅层随机测试漏掉。

## 场景矩阵

| ID | 场景 | 主要风险 | 人工复核点 |
| --- | --- | --- | --- |
| S01 | 读写冒烟路径 | driver 或 monitor 连接错误 | 每个 response 都与 reference memory model 比对 |
| S02 | read miss 与 refill | refill 顺序或 replay response 错误 | 检查 refill beat alignment 与 response timing |
| S03 | write miss allocate | masked write 污染未选中字节 | store 后 readback 全 word 和 byte lane |
| S04 | dirty eviction integrity | 脏 victim 在 replacement 中丢失 | 要求 writeback 先于新 line 安装 |
| S05 | clean eviction 静默性 | clean victim 产生错误 writeback | 观察 writeback channel 是否保持安静 |
| S06 | replacement 压力 | replacement 状态卡住或轮转错误 | 地址偏向同一 set，并保留失败 seed |
| S07 | stall 与 back-pressure | ready 为低时 metadata 漂移 | 断言 request field 在 stall 中保持稳定 |
| S08 | reset recovery | miss/refill 瞬态状态穿过 reset | reset 打在 miss/refill window 内，再跑干净 smoke path |
| S09 | 边界地址 aliasing | tag/index/offset slicing 混淆相邻 line | 相邻 line 与 byte mask 交替访问 |
| S10 | 长随机回归 | 稀有 interleaving 逃过定向测试 | 固定 seed、地址分布、读写比例和 stall knobs |
| S11 | mask 与 offset 矩阵 | full-word traffic 掩盖 byte-lane bug | 混合 low mask、high mask、full mask 和非零 word offset |
| S12 | 事件级 replacement 审计 | 数据仍匹配但 policy state 漂移 | 比对 eviction address、writeback、refill 和 stall events |

## 组件分工

- `CacheDriver`：发送 load/store request，并保持 transaction ID 可追踪。
- `CacheMonitor`：记录 request、response、refill、writeback、stall 和 reset-window event。
- `ReferenceMemory`：scoreboard 使用的 byte-addressable reference model。
- `CacheScoreboard`：检查数据、事件顺序、dirty writeback、replacement 和 mask 语义。
- `CoverageCollector`：记录功能覆盖点并输出 JSON 证据。
- `ReviewJournal`：保存 prompt 轮次、草案问题和人工修正。

当前仓库已经包含证据模型和可执行 Python scoreboard rehearsal。同一套事务接口通过 `src/cachesage_uc/adapters/` 对齐 Picker/Toffee DUT 路径。

## 覆盖策略

只有同时刺激到目标行为，并由 scoreboard 或 monitor 观察到对应效果时，coverpoint 才计入。比如随机流碰巧触发 replacement 并不自动算覆盖，除非同时证明 victim 行为正确。

当前 Python harness 跟踪 23 个功能覆盖点，本地复现命令为：

```powershell
python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json
```

该 run 的目标阈值为 Python harness 覆盖率不低于 90%。RTL/Toffee 实测覆盖率在 Picker-generated DUT 路径运行后独立记录。
