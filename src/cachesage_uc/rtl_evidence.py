from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

from .rtl_coverage import RtlCoverageReport


def parse_verilator_coverage_summary(output: str) -> dict:
    match = re.search(r"Total coverage \((\d+)/(\d+)\)\s+([0-9.]+)%", output)
    if not match:
        raise ValueError("Verilator coverage summary was not found")
    return {
        "covered_points": int(match.group(1)),
        "total_points": int(match.group(2)),
        "percent": float(match.group(3)),
    }


def build_rtl_evidence(
    report: RtlCoverageReport,
    upstream_commit: str,
    tools: Dict[str, str],
    seeds: Iterable[int],
    transactions: int,
    waveform: Optional[str],
    code_coverage: dict,
) -> dict:
    payload = report.to_dict()
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": payload["status"],
        "subject": {
            "name": "XS-MLVP/Example-NutShellCache",
            "upstream_commit": upstream_commit,
        },
        "tools": dict(tools),
        "run": {
            "seeds": list(seeds),
            "transactions": int(transactions),
        },
        "coverage": payload["coverage"],
        "coverpoints": payload["coverpoints"],
        "scoreboard": payload["scoreboard"],
        "artifacts": {
            "waveform": waveform,
            "rtl_code_coverage": dict(code_coverage),
        },
    }


def render_rtl_markdown(evidence: dict) -> str:
    coverage = evidence["coverage"]
    scoreboard = evidence["scoreboard"]
    code_coverage = evidence["artifacts"]["rtl_code_coverage"]
    code_status = code_coverage.get("status", "not_exported")
    code_detail = code_coverage.get("summary") or code_coverage.get("reason") or code_status
    if isinstance(code_detail, dict) and {"covered_points", "total_points", "percent"} <= set(code_detail):
        code_detail = (
            f"{code_detail['covered_points']}/{code_detail['total_points']}"
            f"（{code_detail['percent']:.2f}%）"
        )
    rows = []
    for point in evidence["coverpoints"]:
        sources = "；".join(point.get("sources", [])) or "无"
        rows.append(
            f"| `{point['id']}` | {'已覆盖' if point['covered'] else '未覆盖'} | "
            f"{point['hit_count']} | {sources} |"
        )
    return "\n".join(
        [
            "# CacheSage-UC RTL 实测记录",
            "",
            f"- 上游提交：`{evidence['subject']['upstream_commit']}`",
            f"- 回归 seed：`{', '.join(str(seed) for seed in evidence['run']['seeds'])}`",
            f"- RTL 事务数：`{evidence['run']['transactions']}`",
            f"- RTL 功能覆盖率：`{coverage['covered']}/{coverage['total']}`（`{coverage['percent']:.2f}%`）",
            f"- Scoreboard：`{scoreboard['comparisons']}` 次比较，`{len(scoreboard['failures'])}` 个失败",
            f"- RTL 代码覆盖率：`{code_status}`，{code_detail}",
            "",
            "## 覆盖点明细",
            "",
            "| 覆盖点 | 状态 | 命中次数 | 实测来源 |",
            "|---|---:|---:|---|",
            *rows,
            "",
            "## 证据边界",
            "",
            "RTL 功能覆盖率来自 Toffee 驱动真实 Picker DUT 后的请求、响应和内存侧事件；"
            "RTL 代码覆盖率是 Verilator 对 RTL 行、分支、条件或翻转活动的独立统计，两者不混写。",
            "",
        ]
    )


def write_rtl_evidence(evidence: dict, json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_rtl_markdown(evidence), encoding="utf-8")
