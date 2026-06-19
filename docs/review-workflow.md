# 复核工作流

本项目把生成草案当作 review input，而不是未经检查的验证代码。复核记录是提交材料的一部分，用来说明每次关键改动为什么发生。

## 工作规则

- 草案可以提出计划、框架、prompt 和 first-pass code。
- cache invariant、scoreboard 行为和覆盖率口径必须经过人工复核。
- 任何涉及 scoreboard 的代码都要回到具体 transaction trace 上检查。
- 报告把 Python harness 功能覆盖率、RTL 功能覆盖率和 Verilator 代码覆盖率分开写。
- 机器可读记录放在 `review_journal.jsonl`，面向阅读的摘要放在 `docs/review-catalog.md`。

## 复核表

| 阶段 | 草案问题 | 修正动作 | 工程原因 |
| --- | --- | --- | --- |
| 测试计划草案 | replacement 被写成一个泛化场景 | 拆成 clean eviction、dirty eviction 和 same-set pressure | 这三类失败形态不同，观测点也不同 |
| Scoreboard 设计 | checker 只比较最终 read data | 增加 writeback-before-refill 的 event-order obligation | cache 可能返回正确最终数据却丢掉 dirty victim |
| CRV 约束 | 所有流都使用均匀随机地址 | 加入 same-set bias，同时保留少量 full-range stream | 朴素随机很难稳定触发 replacement pressure |
| 失败分诊 | prompt 直接要求修补 mismatch | 先人工区分 scoreboard bug、DUT bug 或 stimulus bug | 盲目修补会隐藏根因 |
| 报告口径 | 草案把 RTL 覆盖率写得像已实测 | 改为按 planned、Python harness、RTL/Toffee 三类记录 | 公开材料要能被复核 |
| 上游适配 | wrapper 先假设 RTL 形状 | 锁定 Example-NutShellCache，并在 smoke 前检查 layout | 接入要从上游真实流程出发 |
| 写请求驱动 | 直接复用上游 convenience driver | 显式传递 SimpleBus 的 size、mask 和 data | 防止 DUT 与同源参考模型同时接受错误参数 |
| DCache 约束 | 把通用 flush 当作合法场景 | 读取 RTL 断言后改为观察 `io_empty` | 非法激励不能算作验证覆盖 |

## Prompt 模板

后续 UCAgent 轮次采用下面的结构记录：

```text
Target: NutShell Cache, scenario <ID>.
Observed gap: <uncovered coverpoint or failing seed>.
Known invariant: <human-approved cache rule>.
Allowed change: <stimulus constraint | scoreboard check | documentation>.
Do not change: <reference model behavior unless the trace proves it is wrong>.
Return: patch summary, new seed, expected coverage effect, and risks.
```

这个格式能让复核围绕一个具体场景展开，并留下可追踪记录。
