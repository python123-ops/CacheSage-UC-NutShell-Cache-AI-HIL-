from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cachesage_uc.adapters.nutshell_example import inspect_example_tree
from cachesage_uc.adapters.toffee_bridge import to_toffee_cases
from cachesage_uc.verification import VerificationRunner, build_seeded_random_sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CacheSage-UC NutShell smoke bridge.")
    parser.add_argument("--upstream", default="third_party/Example-NutShellCache")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--count", type=int, default=96)
    parser.add_argument("--output", default="reports/nutshell-smoke.json")
    parser.add_argument("--markdown", default="reports/nutshell-smoke.md")
    parser.add_argument("--rtl-coverage-info", default="reports/rtl-code-coverage.info")
    parser.add_argument("--collect-rtl-artifacts", dest="collect_rtl_artifacts", action="store_true", default=True)
    parser.add_argument("--no-collect-rtl-artifacts", dest="collect_rtl_artifacts", action="store_false")
    parser.add_argument("--try-rtl-code-coverage", dest="try_rtl_code_coverage", action="store_true", default=True)
    parser.add_argument("--no-try-rtl-code-coverage", dest="try_rtl_code_coverage", action="store_false")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    upstream = ROOT / args.upstream
    output = ROOT / args.output
    markdown = ROOT / args.markdown
    coverage_info = ROOT / args.rtl_coverage_info
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)

    layout = inspect_example_tree(upstream)
    if not layout.ready:
        payload = {
            "status": "missing_upstream",
            "layout": _public_layout(layout),
            "dependency_note": (
                "未找到 Example-NutShellCache 工作目录；先运行 "
                "`python scripts/fetch_upstream_example.py --lock upstream.lock.json "
                "--dest third_party/Example-NutShellCache` 拉取锁定版本。"
            ),
        }
        _write_outputs(output, markdown, payload)
        print(layout.hint, file=sys.stderr)
        return 2

    transactions = build_seeded_random_sequence(seed=args.seed, count=args.count)
    result = VerificationRunner().run(transactions, seed=args.seed)
    missing_dependencies = _missing_dependencies()
    if missing_dependencies:
        payload = {
            "status": "missing_dependencies",
            "layout": _public_layout(layout),
            "missing_dependencies": missing_dependencies,
            "python_harness": result.to_dict(),
            "toffee_cases_preview": to_toffee_cases(transactions[:8]),
            "rtl_toffee_measured_coverage": None,
            "rtl_artifacts": _empty_artifacts("依赖缺失，未运行 RTL smoke。"),
            "rtl_code_coverage": _coverage_not_exported("依赖缺失，未运行 RTL code coverage 导出。"),
            "dependency_note": (
                "本机缺少 Picker、Toffee、Toffee-Test 或 make；Python harness 已完成，"
                "RTL smoke 需要依赖齐全后运行。"
            ),
            "note": "Python harness 已完成；RTL smoke 当前只记录本机集成依赖状态。",
        }
        _write_outputs(output, markdown, payload)
        print(payload["dependency_note"], file=sys.stderr)
        return 2

    make_results = {
        "gen_dut": _run_make(upstream, "gen_dut"),
        "test": _run_make(upstream, "test"),
    }
    rtl_status = "rtl_smoke_complete" if all(item["returncode"] == 0 for item in make_results.values()) else "rtl_smoke_failed"
    rtl_artifacts = _collect_rtl_artifacts(upstream, enabled=args.collect_rtl_artifacts)
    rtl_code_coverage = _detect_rtl_code_coverage(
        upstream=upstream,
        coverage_info=coverage_info,
        enabled=args.try_rtl_code_coverage,
        smoke_complete=rtl_status == "rtl_smoke_complete",
    )
    payload = {
        "status": rtl_status,
        "layout": _public_layout(layout),
        "python_harness": result.to_dict(),
        "toffee_cases_preview": to_toffee_cases(transactions[:8]),
        "make_results": make_results,
        "rtl_toffee_measured_coverage": None,
        "rtl_artifacts": rtl_artifacts,
        "rtl_code_coverage": rtl_code_coverage,
        "note": "RTL artifact 与 code coverage 只作为 smoke-level 证据；Python harness functional coverage 仍单独记录。",
    }
    _write_outputs(output, markdown, payload)
    print(f"wrote {_display_path(output)}")
    return 0 if result.passed and rtl_status == "rtl_smoke_complete" else 1


def _write_outputs(output: Path, markdown: Path, payload: dict) -> None:
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown.write_text(_render_markdown(payload), encoding="utf-8")


def _public_layout(layout) -> Dict[str, object]:
    payload = layout.to_dict()
    root = Path(str(payload["root"]))
    try:
        payload["root"] = str(root.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        payload["root"] = str(root)
    return payload


def _render_markdown(payload: dict) -> str:
    lines = [
        "# CacheSage-UC NutShell Smoke 记录",
        "",
        f"- 状态：`{payload['status']}`",
    ]
    layout = payload.get("layout", {})
    if layout:
        lines.append(f"- 上游目录：`{layout.get('root')}`")
        lines.append(f"- 缺失路径：{', '.join(layout.get('missing_paths', [])) or '无'}")
    if "python_harness" in payload:
        harness = payload["python_harness"]
        lines.append(
            f"- Python harness：{'通过' if harness['passed'] else '失败'}，"
            f"{harness['coverage']['covered']}/{harness['coverage']['total']} 个 coverpoint"
        )
    if "missing_dependencies" in payload:
        lines.append(f"- 缺失依赖：{', '.join(payload['missing_dependencies'])}")
    if "make_results" in payload:
        for target, result in payload["make_results"].items():
            lines.append(f"- `make {target}`: exit {result['returncode']}")
    if "rtl_artifacts" in payload:
        artifacts = payload["rtl_artifacts"]
        lines.append(f"- RTL artifact manifest：{artifacts.get('status')}，记录 {artifacts.get('count', 0)} 个候选产物")
        for item in artifacts.get("items", [])[:5]:
            lines.append(f"  - `{item['path']}` ({item['kind']}, {item['bytes']} bytes)")
    if "rtl_code_coverage" in payload:
        coverage = payload["rtl_code_coverage"]
        lines.append(f"- RTL code coverage：{coverage.get('status')}，{coverage.get('summary') or coverage.get('reason')}")
    if "dependency_note" in payload:
        lines.append(f"- 依赖说明：{payload['dependency_note']}")
    if "note" in payload:
        lines.append(f"- 记录说明：{payload['note']}")
    lines.append("")
    return "\n".join(lines)


def _missing_dependencies() -> List[str]:
    missing: List[str] = []
    if shutil.which("make") is None:
        missing.append("make")
    if shutil.which("picker") is None:
        missing.append("picker")
    if importlib.util.find_spec("toffee") is None:
        missing.append("toffee")
    if importlib.util.find_spec("toffee_test") is None:
        missing.append("toffee-test")
    return missing


def _run_make(upstream: Path, target: str) -> Dict[str, object]:
    result = subprocess.run(
        ["make", target],
        cwd=upstream,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "returncode": result.returncode,
        "stdout": _sanitize_log(result.stdout[-4000:]),
        "stderr": _sanitize_log(result.stderr[-4000:]),
    }


def _empty_artifacts(reason: str) -> Dict[str, object]:
    return {
        "status": "not_collected",
        "reason": reason,
        "count": 0,
        "items": [],
        "truncated": False,
    }


def _coverage_not_exported(reason: str, candidates: Optional[List[str]] = None, attempts: Optional[List[str]] = None) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "status": "not_exported",
        "reason": reason,
        "candidates": candidates or [],
        "attempts": attempts or [],
    }
    return payload


def _collect_rtl_artifacts(upstream: Path, enabled: bool = True) -> Dict[str, object]:
    if not enabled:
        return _empty_artifacts("artifact manifest collection disabled by CLI flag.")
    if not upstream.exists():
        return _empty_artifacts("upstream directory does not exist.")

    items: List[Dict[str, object]] = []
    for path in upstream.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        kind = _artifact_kind(upstream, path)
        if not kind:
            continue
        stat = path.stat()
        items.append(
            {
                "path": _relative_repo_path(path),
                "upstream_path": path.relative_to(upstream).as_posix(),
                "name": path.name,
                "kind": kind,
                "bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            }
        )

    items.sort(key=lambda item: (str(item["kind"]), str(item["upstream_path"])))
    limit = 80
    return {
        "status": "collected" if items else "none_found",
        "root": _relative_repo_path(upstream),
        "count": len(items),
        "items": items[:limit],
        "truncated": len(items) > limit,
        "note": "Manifest records paths and sizes only; large waveform binaries remain under ignored third_party.",
    }


def _artifact_kind(upstream: Path, path: Path) -> Optional[str]:
    rel = path.relative_to(upstream).as_posix()
    suffix = path.suffix.lower()
    name = path.name.lower()
    rel_lower = rel.lower()
    if suffix in {".fst", ".vcd"}:
        return "waveform"
    if suffix in {".dat", ".info", ".gcda", ".gcno"} or "coverage" in rel_lower or "cover" in name:
        return "coverage_candidate"
    generated_names = {
        "dut.py",
        "example.py",
        "signals.json",
        "top.v",
        "top.sv",
        "filelist.f",
        "cmakelists.txt",
        "makefile",
        "dut_base.cpp",
        "dut_base.hpp",
        "dut_type.hpp",
    }
    if rel.startswith("Cache/") and "build/" not in rel and name in generated_names:
        return "generated_dut"
    return None


def _detect_rtl_code_coverage(upstream: Path, coverage_info: Path, enabled: bool, smoke_complete: bool) -> Dict[str, object]:
    attempts = ["picker export -c via make gen_dut"]
    if not enabled:
        return _coverage_not_exported("RTL code coverage export disabled by CLI flag.", attempts=attempts)
    if not smoke_complete:
        return _coverage_not_exported("RTL smoke did not complete; coverage export skipped.", attempts=attempts)

    candidates = _coverage_candidate_paths(upstream)
    candidate_labels = [_relative_repo_path(path) for path in candidates]
    if not candidates:
        return _coverage_not_exported(
            "Picker coverage flag was enabled, but no Verilator coverage data file was found after smoke.",
            attempts=attempts,
        )

    tool = shutil.which("verilator_coverage")
    if tool is None:
        return _coverage_not_exported(
            "Found coverage candidate files, but verilator_coverage is not available to convert them.",
            candidates=candidate_labels,
            attempts=attempts,
        )

    coverage_info.parent.mkdir(parents=True, exist_ok=True)
    attempts.append("verilator_coverage -write-info")
    result = subprocess.run(
        [tool, "-write-info", str(coverage_info), *[str(path) for path in candidates]],
        cwd=upstream,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not coverage_info.exists():
        payload = _coverage_not_exported(
            "Found coverage candidate files, but verilator_coverage did not produce an LCOV summary.",
            candidates=candidate_labels,
            attempts=attempts,
        )
        payload.update(
            {
                "tool": "verilator_coverage",
                "stdout": _sanitize_log(result.stdout[-1000:]),
                "stderr": _sanitize_log(result.stderr[-1000:]),
            }
        )
        return payload

    _sanitize_lcov_info(coverage_info)
    summary = _parse_lcov_info(coverage_info)
    return {
        "status": "exported",
        "tool": "verilator_coverage",
        "artifact_path": _relative_repo_path(coverage_info),
        "source_candidates": candidate_labels,
        "summary": summary,
        "attempts": attempts,
        "note": "RTL code coverage is smoke-level code coverage and is not mixed with Python harness functional coverage.",
    }


def _coverage_candidate_paths(upstream: Path) -> List[Path]:
    suffixes = {".dat", ".info", ".gcda", ".gcno"}
    candidates: List[Path] = []
    for path in upstream.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel_lower = path.relative_to(upstream).as_posix().lower()
        if path.suffix.lower() in suffixes or "coverage" in rel_lower:
            if path.name != "rtl-code-coverage.info":
                candidates.append(path)
    return sorted(candidates)


def _parse_lcov_info(path: Path) -> Dict[str, object]:
    totals = {"lines_found": 0, "lines_hit": 0, "functions_found": 0, "functions_hit": 0, "branches_found": 0, "branches_hit": 0}
    da_found = 0
    da_hit = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("LF:"):
            totals["lines_found"] += int(line.split(":", 1)[1])
        elif line.startswith("LH:"):
            totals["lines_hit"] += int(line.split(":", 1)[1])
        elif line.startswith("DA:"):
            _, payload = line.split(":", 1)
            parts = payload.split(",")
            if len(parts) >= 2:
                da_found += 1
                if int(parts[1]) > 0:
                    da_hit += 1
        elif line.startswith("FNF:"):
            totals["functions_found"] += int(line.split(":", 1)[1])
        elif line.startswith("FNH:"):
            totals["functions_hit"] += int(line.split(":", 1)[1])
        elif line.startswith("BRF:"):
            totals["branches_found"] += int(line.split(":", 1)[1])
        elif line.startswith("BRH:"):
            totals["branches_hit"] += int(line.split(":", 1)[1])

    if totals["lines_found"] == 0 and da_found:
        totals["lines_found"] = da_found
        totals["lines_hit"] = da_hit

    def percent(hit: int, found: int) -> Optional[float]:
        return None if found == 0 else round(hit * 100.0 / found, 2)

    return {
        **totals,
        "line_percent": percent(totals["lines_hit"], totals["lines_found"]),
        "function_percent": percent(totals["functions_hit"], totals["functions_found"]),
        "branch_percent": percent(totals["branches_hit"], totals["branches_found"]),
    }


def _sanitize_lcov_info(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    root_variants = {
        str(ROOT.resolve()).replace("\\", "/"),
        str(ROOT.resolve()),
    }
    sanitized = text
    for root in root_variants:
        if root:
            sanitized = sanitized.replace(root.rstrip("/") + "/", "")
            sanitized = sanitized.replace(root.rstrip("\\") + "\\", "")
    path.write_text(sanitized, encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


def _sanitize_log(text: str) -> str:
    replacements = {
        str(ROOT.resolve()).replace("\\", "/"): "<repo>",
        str(ROOT.resolve()): "<repo>",
        str(Path.home()).replace("\\", "/"): "<home>",
        str(Path.home()): "<home>",
    }
    sanitized = text
    for old, new in replacements.items():
        if old:
            sanitized = sanitized.replace(old, new)
    return sanitized


def _relative_repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


if __name__ == "__main__":
    raise SystemExit(main())
