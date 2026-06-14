# 上游工程调研记录

调研日期：2026-06-14  
锁定 commit：`cdc9ef7d4dfc3d8fbd969869f6696afe27cfed2a`  
仓库：https://github.com/XS-MLVP/Example-NutShellCache

## 观察到的仓库结构

XS-MLVP/Example-NutShellCache 是本项目对齐 NutShell Cache、Picker 和 Toffee 的公开参考工程。锁定 commit 下的关键路径如下：

| 路径 | 在 CacheSage-UC 中的作用 |
| --- | --- |
| `Makefile` | 提供 `gen_dut`、`test`、`clean` 的流程形状 |
| `rtl/` | Picker 消费的 Verilog RTL source area |
| `src/` | 上游示例的 Python-side testbench/support code |
| `test/` | 上游 tests 和 example regression entry points |
| `pytest.ini` | 说明该示例可从 Python tests 侧运行 |
| `Readme.md` | 记录 Picker、Toffee、Toffee-Test 要求 |
| `nutshell_cache_report_demo.pdf` | 上游展示报告，仅作为版式参考 |

## 不直接纳入第三方源码的原因

参赛仓库需要保持聚焦和可审阅。CacheSage-UC 只保存 `upstream.lock.json` 与 fetch script，既能复现上游来源，也避免把大体量第三方源码塞进提交。

```powershell
python scripts/fetch_upstream_example.py --lock upstream.lock.json --dest third_party/Example-NutShellCache
```

## 适配边界

`src/cachesage_uc/adapters/nutshell_example.py` 检查拉取后的目录是否包含所需路径。`src/cachesage_uc/adapters/toffee_bridge.py` 把当前 `Transaction` 对象映射为 Toffee-style cache request case：

- `op`: `read` 或 `write`；
- `addr`: byte address；
- `data`: 32-bit write data；
- `mask`: byte mask；
- `meta.tag`: scoreboard 使用的 deterministic trace label。

这样 Python harness 和 Toffee DUT 路径可以共享 seed、trace label 和 coverage vocabulary。
