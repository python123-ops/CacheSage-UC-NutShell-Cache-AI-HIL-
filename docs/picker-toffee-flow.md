# Picker / Toffee 流程记录

本文档记录 Python harness 与真实 NutShell Cache RTL 回归的执行路径和证据边界。

## 本地准备

```bash
python -m pip install -e .
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
```

Picker、Toffee 和 Toffee-Test 按上游项目说明安装：

- https://github.com/XS-MLVP/picker
- https://github.com/XS-MLVP/toffee
- https://github.com/XS-MLVP/toffee-test

## 上游命令

在拉取后的上游目录中运行：

```bash
make gen_dut
make test
make clean
```

CacheSage-UC 不修改上游 RTL。项目适配层按真实 SimpleBus 端口显式传递 64 位数据、8 位掩码和 size，并使用独立 Scoreboard 检查读回值。

## CacheSage Smoke 边界

```bash
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
python scripts/run_rtl_regression.py
```

脚本写出的状态包含：

- inspected upstream layout；
- seed 11、count 96 的 Python harness 结果；
- Toffee-style request case 预览；
- `rtl_artifacts`，记录 waveform、generated DUT、coverage candidate 的相对路径、大小和用途。
- `rtl_code_coverage`，记录 Verilator/Picker code coverage 是否导出；成功时写 LCOV 摘要，失败时写 `not_exported` 原因。

## 覆盖率记录约定

CacheSage-UC 固定分成四类数据：

| 类别 | 含义 |
| --- | --- |
| planned coverage | `docs/verification-plan.md` 中定义的功能覆盖点 |
| Python harness measured coverage | `VerificationRunner` 在 reference/candidate cache model 上测得的数据 |
| RTL smoke artifact | Picker-generated DUT 运行后产生的 waveform、generated DUT 和 coverage candidate manifest |
| RTL code coverage | Verilator/Picker coverage 数据可解析后导出的 smoke-level code coverage |
| RTL functional coverage | Toffee 驱动真实 Picker DUT 后，由响应、memory、victim 和 probe 事件命中的 36 点模型；当前为 `34/36（94.44%）` |

RTL 回归使用定向场景和 seed `11/29/73`，共执行 421 条真实 DUT 事务。独立 Scoreboard 完成 199 次读数据比较且无失败；未命中的输入和响应 backpressure 保留为未覆盖。

Verilator `coverage.dat` 经 `verilator_coverage --annotate` 得到 `898/1454（61.00%）`。该数字是 RTL 代码活动覆盖率，不与 `34/36` 功能覆盖率合并。

这个拆分让报告保持可复核：没有实测来源的数据不写成实测结论。
