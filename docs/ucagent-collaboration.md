# UCAgent 与人工复核记录

本项目把 UCAgent 用于场景展开、代码初稿和证据整理，但不把草案直接视为可交付验证环境。每轮改动都要经过人工检查，确认协议参数、Cache 不变量、参考模型独立性和覆盖率数据来源。机器可读记录位于 `review_journal.jsonl`，本页给出其中最关键的工程决策。

## 记录方法

每条记录保存六类信息：任务阶段、草案摘要、受影响模块、人工发现与风险、实际代码修正、修正前后指标。验证命令和产物路径与代码提交绑定，便于从报告反查实现。

| 记录 | 草案或初始假设 | 人工复核发现 | 实际修正 | 可复核结果 |
| --- | --- | --- | --- | --- |
| RV-006 | 复用原有 32 位 Python Transaction 驱动 RTL | DUT 实际为 64 位数据、8 位掩码、64 字节行、128 组、4 路 | 单独建立 `RtlTransaction` 和 `RtlCacheConfig` | 参数和 `0x2000` 同组步长由单元测试锁定 |
| RV-007 | 把上游 smoke 与 Python 23/23 一并当作 RTL 覆盖证据 | 自研事务没有驱动真实 DUT，无法形成端到端功能覆盖率 | 建立 36 点真实 DUT 覆盖模型，命中必须来自响应、内存侧、victim 或 probe 事件 | 真实 DUT 覆盖 `34/36`，未覆盖点单独列出 |
| RV-008 | 只通过输入端口做简单 read/write | replacement 和 coherence 没有直接观测 | 采集 `victim_way_mask`、内存 refill/writeback 和 `io_out_coh` 响应 | replacement、clean/dirty eviction、probe miss/hit/data 均有事件来源 |
| RV-009 | 直接复用上游 `block_write` | 位置参数错位使 data 被传入 size；同源参考模型未报警 | 项目适配器显式传递 `address,size,cmd,mask,data`，另建独立 byte-mask Scoreboard | 写入 `0x1122334455667788` 后真实 DUT 正确读回；199 次比较、0 失败 |
| RV-010 | 对当前 Cache 实例执行通用 flush | RTL 断言表明 DCache 禁止该激励 | 删除非法 flush，改为观察公开 `io_empty` 空闲恢复 | 三个 seed 共 421 条事务完整结束，无 RTL fatal |

## 指标变化

| 项目 | 修正前 | 修正后 |
| --- | ---: | ---: |
| 真实 DUT 功能覆盖率 | 未导出 | `34/36（94.44%）` |
| 真实 DUT Scoreboard | 未建立独立比较 | `199` 次比较，`0` 失败 |
| RTL 代码覆盖率 | 仅有候选文件 | `898/1454（61.00%）` |
| 回归规模 | 上游单一 smoke | 定向场景 + seed `11/29/73`，共 `421` 条事务 |
| 一致性观测 | 无 | probe miss、clean hit、dirty hit、8 beat 数据返回、probe 后重访 |

## 证据边界

- `34/36` 是 Toffee 驱动 Picker 生成 DUT 后得到的功能覆盖率，不是 Python harness 的 `23/23`。
- `61.00%` 是 Verilator code coverage，对应 `coverage.dat` 中的行、条件、分支和翻转等代码活动总计，不等同于功能覆盖率。
- 未命中的 `rtl_input_backpressure` 和 `rtl_response_backpressure` 保留为未覆盖，不通过人工标记补齐。
- `review_journal.jsonl` 中 RV-001 至 RV-005 来自提交历史和复核笔记重建；RV-006 至 RV-010 为开发过程同步记录。

## 复现命令

```bash
source /opt/cachesage-uc-smoke-venv/bin/activate
python scripts/run_rtl_regression.py
python -m unittest discover -s tests -v
```

大体积 `*.fst` 和 `coverage.dat` 保留在本地忽略目录，仓库提交其文件大小、工具版本、覆盖摘要和覆盖点来源。
