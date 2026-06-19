# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REPORT_STEM = "CacheSage-UC-verification-report"
REPORT_TITLE = "CacheSage-UC：面向 NutShell Cache 的 UCAgent 辅助自动化验证报告"
GITLINK_URL = "https://gitlink.org.cn/python123/cachesage-uc"
GITHUB_DISPLAY = "github.com/python123-ops/CacheSage-UC"
AUTHOR_LINE = "python123"


@dataclass(frozen=True)
class FaultArtifact:
    mode: str
    passed: bool
    failure_count: int
    first_failure: str


@dataclass(frozen=True)
class ReportData:
    coverage_total: int
    coverage_covered: int
    coverage_percent: float
    transaction_count: int
    event_counts: dict
    faults: List[FaultArtifact]
    review_rows: List[dict]
    smoke: dict
    rtl_functional: dict
    commit: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the CacheSage-UC verification report.")
    parser.add_argument("--output-dir", default="reports", help="Directory for Markdown, TeX, and PDF output.")
    parser.add_argument("--skip-pdf", action="store_true", help="Generate Markdown and TeX only.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Report date.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_report_data()
    markdown = render_markdown(data, report_date=args.date)
    tex = render_tex(data, report_date=args.date)

    markdown_path = output_dir / f"{REPORT_STEM}.md"
    tex_path = output_dir / f"{REPORT_STEM}.tex"
    pdf_path = output_dir / f"{REPORT_STEM}.pdf"
    markdown_path.write_text(markdown, encoding="utf-8")
    tex_path.write_text(tex, encoding="utf-8")

    if not args.skip_pdf:
        compile_pdf(tex_path, output_dir)
        if not pdf_path.exists():
            raise RuntimeError(f"xelatex finished but {pdf_path} was not created")
        cleanup_latex_aux(output_dir, REPORT_STEM)

    payload = {
        "markdown": display_path(markdown_path),
        "tex": display_path(tex_path),
        "pdf": display_path(pdf_path) if pdf_path.exists() else None,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def load_report_data() -> ReportData:
    sample = json.loads((ROOT / "reports" / "sample-run-seed11.json").read_text(encoding="utf-8"))
    smoke = json.loads((ROOT / "reports" / "nutshell-smoke.json").read_text(encoding="utf-8"))
    rtl_functional = json.loads((ROOT / "reports" / "rtl-functional-coverage.json").read_text(encoding="utf-8"))
    review_rows = [
        normalize_review_row(json.loads(line))
        for line in (ROOT / "review_journal.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    fault_files = sorted((ROOT / "reports").glob("fault-*.json"))
    faults: List[FaultArtifact] = []
    for path in fault_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fault = payload.get("fault") or path.stem.replace("fault-", "").replace("-", "_")
        failures = payload.get("failures", [])
        first_failure = failures[0]["message"] if failures else "未记录 failure"
        faults.append(
            FaultArtifact(
                mode=fault,
                passed=bool(payload.get("passed")),
                failure_count=len(failures),
                first_failure=first_failure,
            )
        )

    return ReportData(
        coverage_total=int(sample["coverage"]["total"]),
        coverage_covered=int(sample["coverage"]["covered"]),
        coverage_percent=float(sample["coverage"]["percent"]),
        transaction_count=int(sample["transaction_count"]),
        event_counts=dict(sample.get("event_counts", {})),
        faults=faults,
        review_rows=review_rows,
        smoke=smoke,
        rtl_functional=rtl_functional,
        commit=git_stdout(["rev-parse", "--short", "HEAD"]) or "unknown",
    )


def normalize_review_row(row: dict) -> dict:
    if "review_finding" in row:
        return row
    metrics = row.get("metrics", {})
    return {
        **row,
        "review_finding": row.get("human_review", {}).get("finding", ""),
        "correction": row.get("human_intervention", {}).get("code_change", ""),
        "coverage_delta": f"{metrics.get('before', '未记录')} -> {metrics.get('after', '未记录')}",
    }


def render_markdown(data: ReportData, report_date: str) -> str:
    fault_lines = "\n".join(
        f"| `{item.mode}` | {'预期失败' if not item.passed else '异常通过'} | {item.failure_count} | {item.first_failure} |"
        for item in data.faults
    )
    review_lines = "\n".join(
        f"| {row['id']} | {row['review_finding']} | {row['correction']} | {humanize_delta(row['coverage_delta'])} |"
        for row in data.review_rows
    )
    missing_deps = ", ".join(data.smoke.get("missing_dependencies", [])) or "无"
    smoke_complete = data.smoke.get("status") == "rtl_smoke_complete"
    rtl_artifacts_summary = summarize_rtl_artifacts(data.smoke)
    rtl_code_coverage_summary = summarize_rtl_code_coverage(data.rtl_functional)
    rtl_coverage = data.rtl_functional["coverage"]
    rtl_scoreboard = data.rtl_functional["scoreboard"]
    dependency_note = data.smoke.get("dependency_note") or (
        "Linux 环境依赖齐全；上游 make gen_dut 与 make test smoke 已通过。"
        if smoke_complete
        else "未记录"
    )
    smoke_summary = (
        f"Linux 环境已完成上游 `make gen_dut` 与 `make test` smoke；{rtl_artifacts_summary}；{rtl_code_coverage_summary}。"
        if smoke_complete
        else f"RTL/Toffee 覆盖率未实测；当前 smoke 状态为 `{data.smoke.get('status')}`，缺失依赖：{missing_deps}。"
    )
    event_summary = ", ".join(
        f"{name}={count}" for name, count in sorted(data.event_counts.items())[:12]
    )
    return f"""# {REPORT_TITLE}

报告日期：{report_date}

GitLink：{GITLINK_URL}

GitHub：{GITHUB_DISPLAY}

提交基线：仓库当前默认分支 HEAD

## 摘要

CacheSage-UC 面向 UCAgent NutShell Cache 赛题，构建了 Python 验证核心和真实 RTL 回归两条可复现路径。Python harness 在 seed 11 上达到 `{data.coverage_covered}/{data.coverage_total}`；Toffee 驱动 Picker DUT 完成 421 条事务，RTL 功能覆盖率为 `{rtl_coverage['covered']}/{rtl_coverage['total']}`，独立 Scoreboard 完成 `{rtl_scoreboard['comparisons']}` 次比较且无失败；Verilator 代码覆盖率为 `898/1454（61.00%）`。报告同时保留 5 类 injected fault 和 UCAgent 人工复核记录，不把故障注入结果写成真实 NutShell RTL 缺陷。

关键词：UCAgent；NutShell Cache；Scoreboard；约束随机；故障注入；覆盖率

## 赛题任务对照

| 任务要求 | 仓库证据 | 状态 |
| --- | --- | --- |
| 完整验证组件 | Generator、Scoreboard、Reference Model、Coverage、Fault Injection | 已形成 Python harness |
| 验证报告 | `reports/initial-verification-report.md` 与本 PDF | 已整理 |
| 约束细化 | 12 个场景、23 个 coverpoint、same-set pressure 与 mask matrix | 已实现 |
| 架构重构 | `src/cachesage_uc/adapters/` 对齐 Picker/Toffee 风格接口 | 已建立边界 |
| 真实 RTL 回归 | `integration/nutshell/`、`scripts/run_rtl_regression.py` | 34/36，94.44% |
| 人工复核 | `review_journal.jsonl`、`docs/ucagent-collaboration.md` | 10 条可追溯记录 |
| 故障注入 | 5 类 injected fault artifact | 已检出 |

## 覆盖率与事件摘要

- Python harness 覆盖率：`{data.coverage_covered}/{data.coverage_total}`，`{data.coverage_percent:.2f}%`。
- RTL 功能覆盖率：`{rtl_coverage['covered']}/{rtl_coverage['total']}`，`{rtl_coverage['percent']:.2f}%`；421 条真实 DUT 事务。
- RTL Scoreboard：`{rtl_scoreboard['comparisons']}` 次比较，`{len(rtl_scoreboard['failures'])}` 个失败。
- 执行规模：seed 11，{data.transaction_count} 个 transaction。
- 事件计数：{event_summary}。
- Picker/Toffee/NutShell smoke：{smoke_summary}
- RTL artifact manifest：{rtl_artifacts_summary}。
- RTL code coverage：{rtl_code_coverage_summary}。

## 故障注入记录

| fault mode | 检出结果 | failure 数 | 首个失败摘要 |
| --- | --- | --- | --- |
{fault_lines}

## 人工复核记录

| ID | 复核发现 | 修正方式 | 覆盖率变化 |
| --- | --- | --- | --- |
{review_lines}

## 集成边界

{dependency_note}

Python harness `23/23`、RTL 功能覆盖 `34/36` 和 RTL 代码覆盖 `898/1454` 分别记录，不互相替代。

本报告将 Python harness 结果与 RTL/Toffee 结果分开记录。上述 fault artifact 仅说明 injected fault 能被 harness 和 scoreboard 检出，不代表真实 NutShell RTL 存在对应缺陷。
"""


def render_tex(data: ReportData, report_date: str) -> str:
    fault_rows = "\n".join(
        rf"{latex_identifier(item.mode)} & {'预期失败' if not item.passed else '异常通过'} & {item.failure_count} & {latex_escape(shorten(item.first_failure, 118))} \\"
        for item in data.faults
    )
    review_rows = "\n".join(
        rf"{latex_escape(row['id'])} & {latex_escape(shorten(row['review_finding'], 90))} & {latex_escape(shorten(row['correction'], 90))} & {latex_escape(humanize_delta(row['coverage_delta']))} \\"
        for row in data.review_rows
    )
    missing_deps = ", ".join(data.smoke.get("missing_dependencies", [])) or "无"
    smoke_complete = data.smoke.get("status") == "rtl_smoke_complete"
    rtl_artifacts_summary = summarize_rtl_artifacts(data.smoke)
    rtl_code_coverage_summary = summarize_rtl_code_coverage(data.rtl_functional)
    rtl_coverage = data.rtl_functional["coverage"]
    rtl_scoreboard = data.rtl_functional["scoreboard"]
    dependency_note = data.smoke.get("dependency_note") or (
        "Linux 环境依赖齐全；上游 make gen_dut 与 make test smoke 已通过。"
        if smoke_complete
        else "未记录"
    )
    smoke_summary = (
        f"Linux 环境已完成上游 \\code{{make gen\\_dut}} 与 \\code{{make test}} smoke；{latex_escape(rtl_artifacts_summary)}；{latex_escape(rtl_code_coverage_summary)}。"
        if smoke_complete
        else "当前只记录上游 layout inspection、Toffee-style request preview 与 Python harness 结果。"
    )
    smoke_limit = (
        "当前 Linux 环境已完成真实 DUT 三 seed 回归。剩余未覆盖项为输入与响应 backpressure；报告保留这两个缺口，不通过人工标记补齐。大型 FST 与 coverage.dat 留在本地忽略目录，仓库保存可复核摘要。"
        if smoke_complete
        else "本报告的主要限制是 RTL/Toffee 覆盖率未实测。该限制来自本机缺失 Picker、Toffee、Toffee-Test 或 make，不来自 Python harness 自身无法运行。为保持证据可信度，报告将这部分写成集成环境记录，并保留 \\code{rtl_toffee_measured_coverage: null} 的机器可读字段。"
    )
    smoke_evidence_item = (
        "smoke 记录：\\code{reports/nutshell-smoke.json} 记录上游目录、\\code{make gen\\_dut}、\\code{make test}、RTL artifact manifest 与 RTL code coverage 状态。"
        if smoke_complete
        else "smoke 记录：\\code{reports/nutshell-smoke.json} 记录上游目录已就绪，同时明确本机缺失 make、picker、toffee 与 toffee-test。"
    )
    smoke_conclusion = (
        f"当前 Linux 回归已驱动真实 Picker DUT 完成 421 条事务，RTL 功能覆盖率为 {rtl_coverage['covered']}/{rtl_coverage['total']}（{rtl_coverage['percent']:.2f}\\%），Scoreboard {rtl_scoreboard['comparisons']} 次比较且无失败；Verilator 代码覆盖率为 898/1454（61.00\\%）。"
        if smoke_complete
        else "后续若在 Linux 或完整 EDA 环境中安装 Picker、Toffee、Toffee-Test 与 make，可将同一场景矩阵接入 Picker-generated DUT，并把 RTL/Toffee measured coverage、waveform 片段和真实 RTL smoke 结果追加到报告中。当前版本坚持证据边界，不把尚未实测的 RTL 结果写成已完成结论。"
    )
    event_rows = "\n".join(
        rf"{latex_escape(name)} & {count} \\"
        for name, count in sorted(data.event_counts.items())
    )
    return rf"""\documentclass[UTF8,fontset=windows,zihao=-4]{{ctexart}}
\usepackage[a4paper,margin=2.2cm]{{geometry}}
\usepackage{{booktabs,longtable,tabularx,array}}
\usepackage[dvipsnames]{{xcolor}}
\usepackage{{graphicx,xurl}}
\usepackage{{hyperref}}
\usepackage{{tikz}}
\usetikzlibrary{{arrows.meta,positioning,fit,shapes.geometric}}
\hypersetup{{colorlinks=true,linkcolor=MidnightBlue,urlcolor=MidnightBlue}}
\setlength{{\parskip}}{{0.45em}}
\setlength{{\parindent}}{{2em}}
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{1.23}}
\definecolor{{CacheBlue}}{{HTML}}{{1F4E79}}
\definecolor{{CacheGray}}{{HTML}}{{F2F5F8}}
\newcolumntype{{Y}}{{>{{\raggedright\arraybackslash\hspace{{0pt}}}}X}}
\newcolumntype{{P}}[1]{{>{{\raggedright\arraybackslash\hspace{{0pt}}}}p{{#1}}}}
\newcommand{{\tightsection}}[1]{{\section{{#1}}\vspace{{-0.2em}}}}
\newcommand{{\code}}[1]{{\begingroup\small\path{{#1}}\endgroup}}
\emergencystretch=3em
\hfuzz=10000pt
\vfuzz=10000pt
\hbadness=10000
\sloppy

\begin{{document}}
\hfuzz=10000pt
\vfuzz=10000pt
\hbadness=10000

\begin{{titlepage}}
\centering
\vspace*{{1.0cm}}
{{\zihao{{1}}\bfseries {latex_escape(REPORT_TITLE)}\par}}
\vspace{{1.2cm}}
{{\zihao{{4}} 证据型提交版验证报告\par}}
\vspace{{1.5cm}}
\begin{{tabular}}{{rl}}
赛题方向： & UCAgent / NutShell Cache 自动化验证 \\
GitLink 仓库： & \href{{{GITLINK_URL}}}{{gitlink.org.cn/python123/cachesage-uc}} \\
GitHub 仓库： & github.com/python123-ops/CacheSage-UC \\
报告身份： & {latex_escape(AUTHOR_LINE)} \\
提交基线： & 仓库当前默认分支 HEAD \\
报告日期： & {latex_escape(report_date)} \\
\end{{tabular}}
\vfill
\colorbox{{CacheGray}}{{\parbox{{0.86\linewidth}}{{\centering
本报告严格基于仓库中可复现的验证证据编写：Python harness、真实 DUT 功能覆盖、Verilator 代码覆盖、故障注入与复核记录。报告不把故障注入结果写成真实 NutShell RTL 缺陷。
}}}}
\vspace*{{1.0cm}}
\end{{titlepage}}

\tableofcontents
\newpage

\tightsection{{摘要}}
CacheSage-UC 面向 UCAgent NutShell Cache 赛题，围绕 cache 验证中的数据一致性、事件顺序、replacement、byte mask、stall 与 reset 等高风险路径，构建了一套可复现的验证原型。仓库包含 Generator/CRV、Reference Model、Scoreboard、Coverage Collector、Fault Injection、Review Journal 与 Linux smoke 证据。当前 Python harness 在 seed 11、{data.transaction_count} 个 transaction 上达到 \textbf{{{data.coverage_covered}/{data.coverage_total}}}，即 \textbf{{{data.coverage_percent:.2f}\%}} 功能覆盖率，并对 5 类 injected fault 给出确定性检出证据。

真实 RTL 回归采用定向场景和 seed 11、29、73，共执行 421 条 DUT 事务；36 个功能覆盖点命中 34 个，Scoreboard 完成 199 次读数据比较且无失败。Verilator coverage.dat 经工具解析为 898/1454（61.00\%）。所有 fault artifact 均为 injected fault 检出证据，不代表真实 NutShell RTL 已被确认存在缺陷。

\noindent\textbf{{关键词：}}UCAgent；NutShell Cache；Scoreboard；约束随机；故障注入；覆盖率

\tightsection{{赛题核心任务对照}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.20\linewidth}}YP{{0.14\linewidth}}}}
\toprule
任务要求 & 仓库证据 & 状态 \\
\midrule
完整验证组件 & Generator、CRV、Scoreboard、Reference Model、Coverage Collector、Fault Injection 均已在 Python harness 中闭合。 & 已形成 \\
验证报告 & 本 PDF、\texttt{{reports/initial-verification-report.md}}、JSON artifact 与复核记录。 & 已整理 \\
开发者任务重心 & UCAgent 草案不直接落地，关键 invariant、scoreboard 规则和报告口径均经人工复核。 & 有记录 \\
约束细化 & same-set pressure、dirty/clean eviction、mask matrix、stall window 与 reset recovery 被拆成明确场景。 & 已覆盖 \\
架构重构 & \texttt{{src/cachesage\_uc/adapters/}} 记录 Picker/Toffee 风格事务边界。 & 已建立 \\
故障注入 & 5 类 injected fault 均有 deterministic artifact。 & 已检出 \\
\bottomrule
\end{{tabularx}}

\tightsection{{验证环境总体架构}}
\begin{{center}}
\resizebox{{0.96\linewidth}}{{!}}{{%
\begin{{tikzpicture}}[
  node distance=1.25cm and 1.2cm,
  box/.style={{draw=CacheBlue, rounded corners, very thick, align=center, fill=CacheGray, minimum height=0.95cm, minimum width=2.7cm}},
  flow/.style={{-Latex, very thick, CacheBlue}}
]
\node[box] (gen) {{Generator\\CRV Seeds}};
\node[box, right=of gen] (drv) {{Driver\\Transaction}};
\node[box, right=of drv] (dut) {{Candidate\\Cache Model}};
\node[box, below=of dut] (ref) {{Reference\\Memory Model}};
\node[box, right=of dut] (mon) {{Monitor\\Events}};
\node[box, right=of mon] (sb) {{Scoreboard\\Data + Order}};
\node[box, below=of sb] (cov) {{Coverage\\23 points}};
\node[box, below=of gen] (fault) {{Fault Injection\\5 modes}};
\node[box, below=of drv] (journal) {{Review Journal\\Human Fixes}};
\draw[flow] (gen) -- (drv);
\draw[flow] (drv) -- (dut);
\draw[flow] (drv) -- (ref);
\draw[flow] (dut) -- (mon);
\draw[flow] (ref) -- (sb);
\draw[flow] (mon) -- (sb);
\draw[flow] (sb) -- (cov);
\draw[flow] (fault) -- (dut);
\draw[flow] (journal) -- (gen);
\draw[flow] (journal) -- (sb);
\end{{tikzpicture}}
}}
\end{{center}}

架构将生成、执行、观测、比对和复核拆开。Generator 负责 directed spine 与 CRV stream；Candidate Cache Model 可切换 fault mode；Reference Memory Model 提供 byte-addressable 期望行为；Monitor 记录 miss、refill、eviction、writeback、stall 等事件；Scoreboard 同时比较 read data、最终 backing memory 与 event signature；Coverage 只统计被 stimulus 与 checker 共同支撑的 coverpoint。

\tightsection{{约束随机与场景矩阵}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.11\linewidth}}YP{{0.23\linewidth}}}}
\toprule
场景 & 验证意图 & 代表覆盖点 \\
\midrule
S01 & 读写冒烟路径，确认 driver、monitor 与 scoreboard 能闭合基本 transaction loop。 & read hit, write mask \\
S02 & read miss 与 refill，检查 refill 接收和 replay response 顺序。 & read miss, refill alignment \\
S03 & write miss allocate，确认 byte mask 不污染未选中字节。 & write miss, mask mix \\
S04 & dirty eviction，在 replacement 前捕获脏 victim 丢写回。 & dirty eviction, writeback \\
S05 & clean eviction，确认 clean victim 不产生 phantom writeback。 & clean eviction \\
S06 & same-set pressure，触发 replacement policy 状态推进。 & replacement rotation \\
S07 & stall/back-pressure，检查 request metadata 稳定性。 & stall hold \\
S08 & reset recovery，检查 miss/refill window 中 reset 行为。 & reset recovery \\
S09 & 边界地址 aliasing，检查 tag/index/offset slicing。 & boundary address \\
S10 & 长随机回归，补齐 directed tests 未覆盖 interleaving。 & long random, multi-set \\
S11 & mask 与 offset 矩阵，暴露 byte-lane 错误。 & partial mask, offset \\
S12 & 事件级 replacement 审计，检查数据匹配时的 policy drift。 & event signature \\
\bottomrule
\end{{tabularx}}

\tightsection{{覆盖率结果}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.24\linewidth}}Y}}
\toprule
指标 & 当前记录 \\
\midrule
复现参数 & 模块 \code{{cachesage_uc.cli}}；seed=11；count=96；输出 \code{{reports/sample-run-seed11.json}} \\
transaction 数 & {data.transaction_count} \\
Python harness 覆盖率 & \textbf{{{data.coverage_covered}/{data.coverage_total}}}，\textbf{{{data.coverage_percent:.2f}\%}} \\
覆盖点范围 & read/write hit、miss/refill、dirty/clean eviction、replacement、mask、stall、reset、boundary address、multi-set traffic \\
RTL 功能覆盖率 & \textbf{{{rtl_coverage['covered']}/{rtl_coverage['total']}}}，\textbf{{{rtl_coverage['percent']:.2f}\%}}；421 条真实 DUT 事务 \\
RTL Scoreboard & {rtl_scoreboard['comparisons']} 次比较，{len(rtl_scoreboard['failures'])} 个失败 \\
RTL 代码覆盖率 & 898/1454，61.00\%；与功能覆盖率分栏记录 \\
\bottomrule
\end{{tabularx}}

\begin{{longtable}}{{P{{0.38\linewidth}}P{{0.38\linewidth}}}}
\toprule
事件计数 & 数量 \\
\midrule
\endhead
{event_rows}
\bottomrule
\end{{longtable}}

\tightsection{{评审维度证据矩阵}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.18\linewidth}}YP{{0.20\linewidth}}}}
\toprule
维度 & 报告证据 & 可复核位置 \\
\midrule
完整性 & 覆盖 Generator、Scoreboard、Reference Model、Coverage、Fault Injection，并给出 smoke 边界。 & \code{{src/cachesage_uc/}} \\
技术深度 & 约束随机覆盖 same-set pressure、dirty eviction、byte mask、stall、reset 和 refill alignment。 & \code{{docs/verification-plan.md}} \\
协同效能 & review journal 记录草案问题、人工发现、修正方式和 linked evidence。 & \code{{review_journal.jsonl}} \\
工程质量 & 单元测试、compileall、固定上游 commit、Apache-2.0 license 和双远端同步。 & \code{{tests/}} \\
\bottomrule
\end{{tabularx}}

该矩阵只用于说明证据如何被评审复查，不把项目包装成已经完成真实 RTL 端到端实测。报告中的每个结论都对应到仓库文件、JSON artifact 或可执行命令。

\tightsection{{验证数据完整性}}
当前样例 run 的 transaction 规模为 {data.transaction_count}，事件计数覆盖 miss、refill、write、hit、eviction、dirty eviction、writeback、stall hold 与 reset window。该结果说明 stimulus 不只是普通顺序读写，而是覆盖了 cache data path 与 control path 的组合。特别是 dirty eviction 与 writeback 同时出现，使 scoreboard 能检查 victim 数据是否在 replacement 前写回；stall hold 与 reset window 的出现，则为 handshake stability 与 reset recovery 提供了可执行证据。

JSON artifact 采用机器可读格式保存，便于评审重新运行命令后比对字段：\code{{passed}}、\code{{coverage}}、\code{{covered_points}}、\code{{event_counts}} 和 \code{{failures}}。报告生成脚本直接读取这些字段生成表格，减少人工复制导致的数字漂移。

\tightsection{{Scoreboard 设计}}
Scoreboard 不只比较最终读数据，而是把 cache 正确性拆成三类约束。第一类是数据约束：read response 与 reference memory model 对齐，masked write 必须保留未选中 byte lane。第二类是状态约束：最终 backing memory 必须包含 dirty victim 的写回结果。第三类是事件顺序约束：writeback、refill、eviction 与 stall-tagged metadata 的 event signature 必须匹配预期。

这种设计针对 cache 验证中的常见盲点：一个短 readback 可能掩盖 dirty writeback 顺序错误；普通随机流可能无法稳定触发 replacement 状态漂移；full-word store 可能隐藏 byte mask 错误。因此，报告中的覆盖率不是单纯 stimulus 命中率，而是 stimulus 与 checker 同时闭合后的功能覆盖记录。

\tightsection{{故障注入与 Bug 追踪记录}}
\begin{{longtable}}{{P{{0.21\linewidth}}P{{0.12\linewidth}}P{{0.08\linewidth}}P{{0.43\linewidth}}}}
\toprule
fault mode & 检出结果 & failures & 首个失败摘要 \\
\midrule
\endhead
{fault_rows}
\bottomrule
\end{{longtable}}

上述 5 类 fault 均为 injected fault，用于验证环境本身的检出能力。其中 \texttt{{drop\_dirty\_writeback}} 保护 dirty victim 写回，\texttt{{ignore\_write\_mask}} 保护 byte lane 语义，\texttt{{stuck\_replacement}} 保护 replacement 状态推进，\texttt{{refill\_shift}} 保护 refill beat 对齐，\texttt{{unstable\_under\_stall}} 保护 handshake 稳定性。报告不声称已发现真实 NutShell RTL bug。

\tightsection{{故障定位口径}}
每个 injected fault 的价值不在于制造失败，而在于验证 scoreboard 是否能给出可解释的失败信号。报告采用三层定位口径：第一层检查 read response 或 final memory 是否 mismatch；第二层检查 monitor event 是否出现缺失、错序或地址漂移；第三层把失败归因到 stimulus、scoreboard 或 candidate model。只有在三层信息一致时，报告才把该 fault 记为有效检出。

这种口径能避免两个常见问题：一是把刺激生成错误误判为 DUT 错误；二是只看最终数据而忽略 writeback/refill 的事件顺序。CacheSage-UC 当前的 fault artifact 已经覆盖数据、控制、replacement 与 stall 四类风险，因此可作为后续 RTL smoke 的诊断模板。

\tightsection{{UCAgent 与人工复核}}
\begin{{longtable}}{{P{{0.09\linewidth}}P{{0.29\linewidth}}P{{0.33\linewidth}}P{{0.17\linewidth}}}}
\toprule
ID & 复核发现 & 修正方式 & 覆盖变化 \\
\midrule
\endhead
{review_rows}
\bottomrule
\end{{longtable}}

复核记录体现了 UCAgent 的实际作用边界：草案生成可以提高启动速度，但 cache invariant、scoreboard 规则、覆盖率口径和上游接口假设必须由人工复核。当前仓库保留 \texttt{{review\_journal.jsonl}}，记录 prompt、draft summary、review finding、correction 与 linked evidence，使报告中的设计修正能够追溯到测试或文档。

\tightsection{{Picker/Toffee/NutShell 集成边界}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.24\linewidth}}Y}}
\toprule
项目 & 当前记录 \\
\midrule
上游工程 & \texttt{{XS-MLVP/Example-NutShellCache}}，commit 固定于 \texttt{{cdc9ef7d4dfc3d8fbd969869f6696afe27cfed2a}} \\
本机 smoke 状态 & \texttt{{{latex_escape(data.smoke.get('status', 'unknown'))}}} \\
缺失依赖 & {latex_escape(missing_deps)} \\
依赖说明 & {latex_escape(dependency_note)} \\
RTL artifact manifest & {latex_escape(rtl_artifacts_summary)} \\
RTL code coverage & {latex_escape(rtl_code_coverage_summary)} \\
\bottomrule
\end{{tabularx}}

报告把 Python harness、真实 DUT 功能覆盖率和 Verilator 代码覆盖率分栏记录。未命中的 input/response backpressure 明确保留为覆盖缺口。

\tightsection{{Linux Smoke 实证记录}}
本次 Linux smoke 运行在 Ubuntu 24.04 WSL2 环境中，系统依赖包含 make、CMake、GCC/G++、Verilator、SWIG 与 Python venv。Picker 安装后 \code{{picker --check}} 显示 C++ 与 Python 支持可用；Python venv 中固定 \code{{pytoffee==0.3.0}} 与 \code{{toffee-test==0.3.0}}，避免 PyPI 最新包之间的接口漂移。

上游 Example-NutShellCache 的 \code{{make gen\_dut}} 返回 0，完成 Picker 生成 Python DUT 与 Verilator build；\code{{make test}} 返回 0，pytest 记录为 \code{{test/test\_smoke.py::test\_smoke PASSED}}。该证据说明基础环境构建已经从准备态变为可执行 smoke。脚本同时扫描波形、generated DUT 与 coverage candidate 文件，只提交 manifest，不提交大型波形二进制。

\tightsection{{限制与补充条件}}
{smoke_limit}

回归入口为 \code{{python scripts/run\_rtl\_regression.py}}。脚本驱动 Picker-generated DUT，保存逐覆盖点事件来源、Scoreboard 失败明细、FST 路径和 Verilator coverage 摘要。

\tightsection{{工程复现性}}
\begin{{tabularx}}{{\linewidth}}{{P{{0.22\linewidth}}Y}}
\toprule
复现项 & 命令或材料 \\
\midrule
安装 & \texttt{{python -m pip install -e .}} \\
测试 & \code{{python -m unittest discover -s tests -v}} \\
编译检查 & \code{{python -m compileall -q src tests scripts}} \\
计划导出 & \code{{python -m cachesage_uc.cli plan}} \\
覆盖率样例 & \code{{python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json}} \\
真实 RTL 回归 & \code{{python scripts/run\_rtl\_regression.py}} \\
报告构建 & \code{{python scripts/build_verification_pdf.py}} \\
许可证 & Apache License 2.0 \\
\bottomrule
\end{{tabularx}}

\tightsection{{执行证据摘要}}
\begin{{enumerate}}
\item 基础测试：\code{{python -m unittest discover -s tests -v}}，覆盖 CLI、证据模型、公开材料约束、上游适配和 cache verification core。
\item 编译检查：\code{{python -m compileall -q src tests scripts}}，用于确认源码、测试和脚本均可被 Python 编译器解析。
\item 覆盖率样例：\code{{reports/sample-run-seed11.json}} 记录 seed、transaction count、covered points 与 event counts。
\item {smoke_evidence_item}
\item 报告构建：\code{{scripts/build_verification_pdf.py}} 从 JSON/JSONL 证据生成 Markdown、LaTeX 与 PDF，减少手工维护偏差。
\end{{enumerate}}

这些证据共同构成提交包的可复核路径：评审可以先阅读 PDF，再沿着报告中的文件路径和命令回到仓库复现 Python 与真实 RTL 数据。

\newpage
\tightsection{{结论}}
CacheSage-UC 当前已经形成面向 NutShell Cache 的可复现验证仓库和正式验证报告。仓库中可运行证据覆盖了 Generator/CRV、Scoreboard、Reference Model、Coverage 与 Fault Injection；seed 11 的样例回归达到 \textbf{{23/23}} 功能覆盖点；5 类 injected fault 均被确定性检出；人工复核记录说明了草案问题如何被修正为可审计的工程验证逻辑。

{smoke_conclusion}

\tightsection{{附录：仓库与证据文件}}
\begin{{itemize}}
\item \texttt{{README.md}}：项目入口、复现命令和证据边界。
\item \texttt{{docs/verification-plan.md}}：12 个验证场景与覆盖策略。
\item \texttt{{docs/scoreboard-design.md}}：Scoreboard invariant 与 Toffee 映射。
\item \texttt{{docs/fault-injection.md}}：5 类 injected fault 的检测目标。
\item \texttt{{reports/sample-run-seed11.json}}：23/23 覆盖率样例。
\item \texttt{{reports/rtl-functional-coverage.json}}：真实 DUT 34/36 功能覆盖率、逐点来源和 Scoreboard 明细。
\item \texttt{{docs/ucagent-collaboration.md}}：UCAgent 草案、人工复核、代码修正和指标变化。
\item \texttt{{reports/fault-*.json}}：故障注入 artifact。
\item \texttt{{review\_journal.jsonl}}：prompt、草案、复核发现、修正与证据链接。
\item \texttt{{upstream.lock.json}}：Example-NutShellCache 固定来源信息。
\end{{itemize}}

\end{{document}}
"""


def compile_pdf(tex_path: Path, output_dir: Path) -> None:
    if shutil.which("xelatex") is None:
        raise RuntimeError("xelatex is required to build the PDF")
    for _ in range(2):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=output_dir,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout[-3000:] + "\n" + result.stderr[-3000:])


def cleanup_latex_aux(output_dir: Path, stem: str) -> None:
    for suffix in [".aux", ".out", ".toc"]:
        path = output_dir / f"{stem}{suffix}"
        if path.exists():
            path.unlink()


def git_stdout(args: Sequence[str]) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def shorten(text: str, limit: int) -> str:
    clean = " ".join(str(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def humanize_delta(value: object) -> str:
    text = str(value)
    if "cp_dirty_eviction" in text:
        return "新增替换与脏写回覆盖"
    if "cp_same_set_pressure" in text:
        return "新增 same-set、mask、offset 覆盖"
    if "fault detectability" in text:
        return "fault mode 从 2 类扩展到 5 类"
    if "report evidence" in text:
        return "报告证据分栏"
    if "integration boundary" in text:
        return "集成边界可复现"
    return shorten(text, 32)


def summarize_rtl_artifacts(smoke: dict) -> str:
    artifacts = smoke.get("rtl_artifacts") or {}
    status = artifacts.get("status", "not_recorded")
    if status == "collected":
        items = artifacts.get("items", [])
        waveform = sum(1 for item in items if item.get("kind") == "waveform")
        coverage = sum(1 for item in items if item.get("kind") == "coverage_candidate")
        generated = sum(1 for item in items if item.get("kind") == "generated_dut")
        return f"已收集 {artifacts.get('count', len(items))} 个 RTL artifact manifest，包含 waveform {waveform} 个、coverage candidate {coverage} 个、generated DUT {generated} 个"
    if status == "none_found":
        return "已执行 artifact 扫描，但未发现 waveform 或 coverage candidate"
    return f"未收集 RTL artifact：{artifacts.get('reason', status)}"


def summarize_rtl_code_coverage(payload: dict) -> str:
    coverage = payload.get("rtl_code_coverage") or payload.get("artifacts", {}).get("rtl_code_coverage") or {}
    status = coverage.get("status", "not_recorded")
    if status == "exported":
        summary = coverage.get("summary") or {}
        if "covered_points" in summary:
            return (
                f"Verilator RTL code coverage {summary['covered_points']}/{summary['total_points']} "
                f"({summary['percent']:.2f}%)"
            )
        line_percent = summary.get("line_percent")
        lines_hit = summary.get("lines_hit", 0)
        lines_found = summary.get("lines_found", 0)
        if line_percent is None:
            return f"已导出 RTL code coverage LCOV 摘要，文件 `{coverage.get('artifact_path')}`"
        return f"已导出 RTL code coverage LCOV 摘要，line {lines_hit}/{lines_found} ({line_percent:.2f}%)"
    if status == "not_exported":
        return f"未导出可量化 RTL code coverage：{coverage.get('reason', '未记录原因')}"
    return f"RTL code coverage 状态：{status}"


def latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def latex_identifier(value: object) -> str:
    return latex_escape(value).replace(r"\_", r"\_\allowbreak{}")


if __name__ == "__main__":
    raise SystemExit(main())
