# Picker / Toffee 流程记录

本文档记录当前 Python harness 到真实 NutShell Cache RTL flow 的执行路径和证据边界。

## 本地准备

```powershell
python -m pip install -e .
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
```

Picker、Toffee 和 Toffee-Test 按上游项目说明安装：

- https://github.com/XS-MLVP/picker
- https://github.com/XS-MLVP/toffee
- https://github.com/XS-MLVP/toffee-test

## 上游命令

在拉取后的上游目录中运行：

```powershell
make gen_dut
make test
make clean
```

CacheSage-UC 不直接假设 RTL interface。适配层先检查上游目录结构，再把现有 transaction stream 映射成 Toffee-style request case。

## CacheSage Smoke 边界

```powershell
python scripts/run_nutshell_smoke.py --upstream third_party/Example-NutShellCache
```

脚本写出的状态包含：

- inspected upstream layout；
- seed 11、count 96 的 Python harness 结果；
- Toffee-style request case 预览；
- `rtl_artifacts`，记录 waveform、generated DUT、coverage candidate 的相对路径、大小和用途。
- `rtl_code_coverage`，记录 Verilator/Picker code coverage 是否导出；成功时写 LCOV 摘要，失败时写 `not_exported` 原因。

## 覆盖率记录约定

CacheSage-UC 固定分成三类数据：

| 类别 | 含义 |
| --- | --- |
| planned coverage | `docs/verification-plan.md` 中定义的功能覆盖点 |
| Python harness measured coverage | `VerificationRunner` 在 reference/candidate cache model 上测得的数据 |
| RTL smoke artifact | Picker-generated DUT 运行后产生的 waveform、generated DUT 和 coverage candidate manifest |
| RTL code coverage | Verilator/Picker coverage 数据可解析后导出的 smoke-level code coverage |
| RTL functional coverage | 后续把当前 23 个 functional coverpoint 接入真实 DUT monitor 后再记录 |

这个拆分让报告保持可复核：没有实测来源的数据不写成实测结论。
