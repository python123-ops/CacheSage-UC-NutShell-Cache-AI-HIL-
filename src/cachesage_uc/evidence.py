from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class CoveragePoint:
    identifier: str
    description: str
    covered: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "description": self.description,
            "covered": self.covered,
        }


@dataclass(frozen=True)
class Scenario:
    identifier: str
    name: str
    intent: str
    method: str
    coverage_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "intent": self.intent,
            "method": self.method,
            "coverage_points": list(self.coverage_points),
        }


@dataclass(frozen=True)
class Intervention:
    stage: str
    draft_summary: str
    review_action: str
    lesson: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "stage": self.stage,
            "draft_summary": self.draft_summary,
            "review_action": self.review_action,
            "lesson": self.lesson,
        }


@dataclass(frozen=True)
class CoverageSummary:
    total: int
    covered: int
    percent: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "total": self.total,
            "covered": self.covered,
            "percent": self.percent,
        }


@dataclass(frozen=True)
class VerificationPlan:
    title: str
    dut: str
    scenarios: List[Scenario]
    coverage_points: List[CoveragePoint]

    def to_dict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "dut": self.dut,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "coverage_points": [point.to_dict() for point in self.coverage_points],
        }


@dataclass(frozen=True)
class EvidenceBundle:
    plan: VerificationPlan
    interventions: List[Intervention]
    fault_injection: List[str] = field(default_factory=list)

    def coverage_summary(self) -> CoverageSummary:
        total = len(self.plan.coverage_points)
        covered = sum(1 for point in self.plan.coverage_points if point.covered)
        percent = 0.0 if total == 0 else round(covered * 100.0 / total, 2)
        return CoverageSummary(total=total, covered=covered, percent=percent)

    def to_dict(self) -> Dict[str, object]:
        return {
            **self.plan.to_dict(),
            "coverage_summary": self.coverage_summary().to_dict(),
            "interventions": [item.to_dict() for item in self.interventions],
            "fault_injection": list(self.fault_injection),
        }


def build_default_bundle() -> EvidenceBundle:
    coverage_points = [
        CoveragePoint("cp_read_hit", "read hit 稳定返回数据，不触发 refill"),
        CoveragePoint("cp_write_hit_mask", "write hit 按 byte mask 只更新选中字节"),
        CoveragePoint("cp_read_miss_refill", "read miss 发起 refill 并重放 load 响应"),
        CoveragePoint("cp_write_miss_allocate", "write miss 分配 cache line 并保持 mask 语义"),
        CoveragePoint("cp_dirty_eviction", "dirty eviction 在替换前写回 victim"),
        CoveragePoint("cp_clean_eviction", "clean eviction 不产生多余 writeback"),
        CoveragePoint("cp_replacement_rotation", "replacement 状态在冲突压力下推进"),
        CoveragePoint("cp_refill_alignment", "refill beat 落在预期 line offset"),
        CoveragePoint("cp_stall_hold", "stall/back-pressure 期间请求元数据保持稳定"),
        CoveragePoint("cp_reset_recovery", "reset 清空瞬态状态后再接收新流量"),
        CoveragePoint("cp_boundary_address", "边界地址不会 alias 到相邻 cache line"),
        CoveragePoint("cp_long_random", "长随机流与 reference memory model 保持一致"),
        CoveragePoint("cp_same_set_pressure", "同 set 冲突流量触发 replacement 压力"),
        CoveragePoint("cp_partial_mask_low", "低字节 mask 写入保留未选中高字节"),
        CoveragePoint("cp_partial_mask_high", "高字节 mask 写入保留未选中低字节"),
        CoveragePoint("cp_alternating_read_write", "读写交替流保持顺序稳定"),
        CoveragePoint("cp_full_line_mask", "full-line word 写入与 masked store 路径兼容"),
        CoveragePoint("cp_multi_set_traffic", "流量覆盖多个 cache set"),
        CoveragePoint("cp_writeback_observed", "monitor 能观察 dirty victim writeback"),
        CoveragePoint("cp_read_after_write", "read-after-write 返回最近一次选中字节"),
        CoveragePoint("cp_offset_word_access", "访问 line 内非零 word offset"),
        CoveragePoint("cp_mask_mix", "回归包含多种 byte mask 形状"),
        CoveragePoint("cp_refill_after_dirty_evict", "dirty eviction 后 refill 的事件顺序保持正确"),
    ]
    scenarios = [
        Scenario(
            "S01",
            "读写冒烟路径",
            "确认 Python driver、monitor 和 scoreboard 能闭合一个基本 cache transaction loop。",
            "对同一 cache line 执行定向 load/store，并用 reference memory model 比对响应。",
            ["cp_read_hit", "cp_write_hit_mask", "cp_read_after_write"],
        ),
        Scenario(
            "S02",
            "read miss 与 refill",
            "覆盖 miss 请求、refill 接收和重放响应顺序。",
            "使用冷读序列和确定性的下游 memory latency 检查 refill beat 对齐。",
            ["cp_read_miss_refill", "cp_refill_alignment"],
        ),
        Scenario(
            "S03",
            "write miss allocate",
            "检查 write-allocate 行为和 miss 后的 byte mask 保持。",
            "对冷 line 做 masked store，再 readback 暴露未选中字节污染。",
            ["cp_write_miss_allocate", "cp_write_hit_mask", "cp_mask_mix"],
        ),
        Scenario(
            "S04",
            "dirty eviction integrity",
            "在 replacement 安装新 line 前捕获脏 victim 丢写回问题。",
            "填满一个 set、写脏 victim、强制替换，再从 memory 读取被替换地址。",
            ["cp_dirty_eviction", "cp_writeback_observed", "cp_refill_after_dirty_evict"],
        ),
        Scenario(
            "S05",
            "clean eviction 静默性",
            "确认 clean victim 不会产生 phantom writeback。",
            "使用冲突流量，并由 monitor 断言 writeback channel 保持安静。",
            ["cp_clean_eviction", "cp_replacement_rotation"],
        ),
        Scenario(
            "S06",
            "replacement 压力",
            "持续同 set 冲突，直到 replacement policy 状态错误可见。",
            "CRV 地址约束到同一 set，失败 seed 可重放。",
            ["cp_replacement_rotation", "cp_same_set_pressure", "cp_long_random"],
        ),
        Scenario(
            "S07",
            "stall 与 back-pressure",
            "验证 request、refill 或 response channel stall 时元数据保持稳定。",
            "在各 handshake 边界注入随机 stall，并由 scoreboard 检查事件顺序。",
            ["cp_stall_hold", "cp_refill_alignment"],
        ),
        Scenario(
            "S08",
            "reset recovery",
            "检查 reset 会取消 miss/refill 窗口中的瞬态 cache 活动。",
            "在 miss/refill window 内打 reset pulse，随后运行干净的 smoke sequence。",
            ["cp_reset_recovery", "cp_read_miss_refill"],
        ),
        Scenario(
            "S09",
            "边界地址 aliasing",
            "防住 line offset、tag/index slicing 在边界地址上的错误。",
            "相邻 line 交替访问，混合 byte mask 后再 readback。",
            ["cp_boundary_address", "cp_offset_word_access", "cp_write_hit_mask"],
        ),
        Scenario(
            "S10",
            "长随机回归",
            "用 coverage hole 和 scoreboard mismatch 驱动复盘。",
            "固定 seed 的 CRV stream，包含地址分布、读写比例和 stall knobs。",
            ["cp_long_random", "cp_dirty_eviction", "cp_stall_hold", "cp_multi_set_traffic"],
        ),
        Scenario(
            "S11",
            "mask 与 offset 矩阵",
            "暴露 full-word traffic 容易掩盖的 byte-lane 错误。",
            "组合 low mask、high mask、full mask 和非零 word offset store，并立即 readback。",
            ["cp_partial_mask_low", "cp_partial_mask_high", "cp_full_line_mask", "cp_mask_mix"],
        ),
        Scenario(
            "S12",
            "事件级 replacement 审计",
            "即使架构读数据仍然匹配，也要捕获 replacement 状态漂移。",
            "比对 eviction address、writeback、refill 与 stall metadata 的 monitor event signature。",
            ["cp_same_set_pressure", "cp_writeback_observed", "cp_refill_after_dirty_evict"],
        ),
    ]
    interventions = [
        Intervention(
            "测试计划草案",
            "最初草案列出了 read/write hit 和 miss，但把 replacement 合并成单一泛化场景。",
            "把 replacement 拆成 clean eviction、dirty eviction 和 same-set pressure 三类，并补上 scoreboard 观察点。",
            "覆盖率要命名被保护的 cache invariant，而不只是列操作类别。",
        ),
        Intervention(
            "Scoreboard 设计",
            "草稿 checker 只比对最终 read data，忽略 writeback order。",
            "补上 scoreboard 约束：victim writeback 必须发生在 refill installation 之前。",
            "Cache 正确性不仅看最终内存内容，也要看关键事件顺序。",
        ),
        Intervention(
            "CRV 约束",
            "第一版随机流使用均匀地址，很难快速打到 replacement pressure。",
            "把地址生成偏向同一个 set，同时保留少量 full-range traffic。",
            "有效覆盖来自成形随机和少量定向 invariant 的组合。",
        ),
        Intervention(
            "失败分诊",
            "初版分诊记录倾向于直接按 waveform 摘要修补 mismatch。",
            "调整为先区分 scoreboard bug、DUT bug 或 stimulus bug，再决定修正位置。",
            "补丁只有建立在可信工程诊断上才有意义。",
        ),
        Intervention(
            "报告口径",
            "初版报告把计划覆盖率写得像已经完成的 RTL 覆盖率。",
            "改为分别记录 planned coverpoints、Python harness 数据和 RTL/Toffee 实测数据。",
            "公开材料可以说明目标，但覆盖率证据必须可审计。",
        ),
    ]
    faults = [
        "drop_dirty_writeback: dirty victim 在 replacement 前未写回",
        "ignore_write_mask: store hit 忽略 byte mask",
        "stuck_replacement: eviction 后 replacement pointer 不推进",
        "refill_shift: refill beat index 偏移一个 word",
        "unstable_under_stall: downstream ready 为低时 request metadata/data 发生变化",
    ]
    return EvidenceBundle(
        plan=VerificationPlan(
            title="CacheSage-UC NutShell Cache 验证计划",
            dut="NutShell Cache",
            scenarios=scenarios,
            coverage_points=coverage_points,
        ),
        interventions=interventions,
        fault_injection=faults,
    )


def render_markdown_report(bundle: EvidenceBundle) -> str:
    from .verification import (
        FaultMode,
        VerificationRunner,
        build_fault_sequence,
        build_seeded_random_sequence,
    )

    summary = bundle.coverage_summary()
    runner = VerificationRunner()
    smoke_result = runner.run(build_seeded_random_sequence(seed=11, count=96), seed=11)
    fault_results = {
        fault: runner.run(build_fault_sequence(fault), fault=fault)
        for fault in FaultMode
        if fault is not FaultMode.NONE
    }

    lines = [
        "# CacheSage-UC 验证记录",
        "",
        "本记录对应 UCAgent NutShell Cache 方向的当前工程状态。文档把计划覆盖点、Python harness 实测结果、"
        "RTL/Toffee 环境记录分开描述，避免把尚未运行的 RTL 数据写成已经完成的结论。",
        "",
        "## 证据边界",
        "",
        "| 证据类别 | 当前状态 | 已记录数据 |",
        "| --- | --- | --- |",
        f"| 计划功能覆盖点 | 已定义 | {summary.total} 个 coverpoint，覆盖 {len(bundle.plan.scenarios)} 个场景 |",
        f"| Python harness 实测覆盖率 | 已测量 | seed 11、96 个 transaction，{smoke_result.coverage.covered}/{smoke_result.coverage.total} ({smoke_result.coverage.percent:.2f}%) |",
        "| RTL/Toffee 实测覆盖率 | 环境记录 | 本机依赖齐全并运行 Picker/Toffee smoke 后单独记录 |",
        "",
        "## 可执行 Harness 快照",
        "",
        "| 命令 | 结果 | 证据 |",
        "| --- | --- | --- |",
        "| `python -m cachesage_uc.cli run --seed 11 --count 96 --output reports/sample-run-seed11.json` | "
        f"{'通过' if smoke_result.passed else '失败'} | "
        f"{smoke_result.transaction_count} 个 transaction，{smoke_result.coverage.percent:.2f}% coverpoint |",
        "",
        "## 场景矩阵",
        "",
        "| ID | 场景 | 验证意图 | 覆盖点 |",
        "| --- | --- | --- | --- |",
    ]
    for scenario in bundle.plan.scenarios:
        coverage = ", ".join(scenario.coverage_points)
        lines.append(f"| {scenario.identifier} | {scenario.name} | {scenario.intent} | {coverage} |")

    lines.extend(
        [
            "",
            "## 设计复盘与修正记录",
            "",
            "| 阶段 | 草案摘要 | 复核修正 | 经验记录 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in bundle.interventions:
        lines.append(f"| {item.stage} | {item.draft_summary} | {item.review_action} | {item.lesson} |")

    lines.extend(
        [
            "",
            "## 故障注入记录",
            "",
            "| fault mode | 结果 | 首个失败摘要 |",
            "| --- | --- | --- |",
        ]
    )
    for fault, result in fault_results.items():
        first_failure = result.failures[0].message if result.failures else "未记录失败"
        lines.append(
            f"| `{fault.value}` | {'预期失败' if not result.passed else '异常通过'} | {first_failure} |"
        )

    lines.extend(["", "## 故障模型目录", ""])
    for fault in bundle.fault_injection:
        lines.append(f"- {fault}")

    lines.extend(
        [
            "",
            "## 集成环境记录",
            "",
            "当前仓库已经提供 Picker/Toffee 适配边界、上游 Example-NutShellCache 锁定信息和 smoke 脚本。"
            "若本机没有安装 Picker、Toffee、Toffee-Test 或 make，RTL smoke 会记录依赖状态，"
            "Python harness 回归仍可独立复现。本项目不声称已经发现真实 NutShell RTL bug；"
            "现有 fault artifact 用于证明 injected fault 可被 harness 和 scoreboard 检出。",
            "",
        ]
    )
    return "\n".join(lines)
