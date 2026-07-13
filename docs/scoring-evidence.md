# 官方评分证据矩阵

本页按比赛官网的两套口径交叉整理仓库证据。它用于帮助评审定位材料，不代表项目自行承诺或推定最终得分。比赛页面显示赛期已于 2026-07-11 结束；2026-07-13 的仓库更新属于赛后公开材料完善，不表示评审系统已重新接收。

比赛页面：https://www.gitlink.org.cn/competitions/track1_UCAgent

GitLink：https://gitlink.org.cn/python123/cachesage-uc

GitHub：https://github.com/python123-ops/CacheSage-UC-NutShell-Cache-AI-HIL-

## 四个总维度

| 官方维度 | 权重 | 仓库证据 | 复核方式 |
| --- | ---: | --- | --- |
| 项目完整度 | 40% | `src/`、`integration/`、`tests/`、`reports/`、Apache-2.0 `LICENSE` | `python scripts/verify_acceptance.py --mode portable` |
| 技术深度 | 30% | 独立 Scoreboard、36 点真实 DUT 覆盖、backpressure handshake trace、5 类 injected fault | 阅读 `docs/scoreboard-design.md` 与 `reports/rtl-functional-coverage.json` |
| AI 使用效率 | 20% | `review_journal.jsonl`、`docs/ucagent-collaboration.md` 记录草案、人工发现、修正及证据链接 | 区分 RV-001～005 重建记录与 RV-006～010 同期记录 |
| 工程质量 | 10% | 上游 commit 锁定、跨平台验收、Python 3.8/当前版本 CI、报告和演示稿生成脚本 | `git diff --check` 与 GitHub Actions |

## 详细 100 分口径

| 官方细项 | 分值 | 已提供证据 | 边界说明 |
| --- | ---: | --- | --- |
| 基础环境与工程搭建 | 20 | `upstream.lock.json`、Picker 生成 DUT、Toffee/Verilator 版本、固定复现入口 | 第三方源码不 vendoring；本地大型 FST/coverage.dat 不提交 |
| 人工介入与优化 | 25 | RV-006～010 的参数、证据、场景、驱动和约束修正；UCAgent 缺陷与人工修正对比 | 不把重建笔记写成同期开发记录 |
| 功能覆盖率 | 15 | 真实 DUT `36/36（100.00%）`；437 条事务；207 次 Scoreboard 比较且零失败 | Verilator `898/1454（61.00%）` 单独列示，不冒充功能覆盖 |
| 协作过程 | 20 | Prompt 模板、review journal、命令、产物、linked evidence | 不隐藏 UCAgent 使用，也不伪造纯人工开发历史 |
| 工程与可复现性 | 20 | portable/full 两级验收、CI、PDF/PPT 构建、双远程同步检查 | full 模式依赖 Linux/WSL 与已锁定上游环境 |

## 本轮闭环证据

- `rtl_input_backpressure`：`io_in_req_valid/io_in_req_ready` 实测等待 2 周期，请求 payload 稳定。
- `rtl_response_backpressure`：`io_in_resp_valid/io_in_resp_ready` 实测等待 3 周期，响应 payload 稳定。
- 8 条预热行内读响应按序进入独立 Scoreboard；覆盖点不是手工补标。
- evidence v2 只有在 `36/36` 且 Scoreboard 零失败时使用 `rtl_functional_coverage_complete`。
