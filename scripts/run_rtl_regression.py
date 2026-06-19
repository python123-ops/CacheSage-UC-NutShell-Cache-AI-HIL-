from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cachesage_uc.rtl_evidence import parse_verilator_coverage_summary, render_rtl_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 NutShell Cache 的 Toffee RTL 功能覆盖率回归。")
    parser.add_argument("--upstream", default="third_party/Example-NutShellCache")
    parser.add_argument("--output", default="reports/rtl-functional-coverage.json")
    parser.add_argument("--markdown", default="reports/rtl-functional-coverage.md")
    parser.add_argument("--artifact-dir", default="artifacts/rtl")
    return parser


def _version(command: list[str], fallback: str) -> str:
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError:
        return fallback
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else fallback


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    upstream = (ROOT / args.upstream).resolve()
    output = (ROOT / args.output).resolve()
    markdown = (ROOT / args.markdown).resolve()
    artifact_dir = (ROOT / args.artifact_dir).resolve()
    generated_dut = upstream / "Cache" / "_UT_Cache.so"
    if not generated_dut.exists():
        print("未找到 Picker 生成的 DUT，请先在上游目录运行 `make gen_dut`。", file=sys.stderr)
        return 2

    artifact_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": os.pathsep.join(
                [str(ROOT / "src"), str(upstream), str(upstream / "src"), env.get("PYTHONPATH", "")]
            ),
            "CACHESAGE_UPSTREAM": str(upstream),
            "CACHESAGE_RTL_ARTIFACT_DIR": str(artifact_dir),
            "CACHESAGE_RTL_OUTPUT_JSON": str(output),
            "CACHESAGE_RTL_OUTPUT_MARKDOWN": str(markdown),
            "CACHESAGE_PICKER_VERSION": _version(["picker", "--version"], "source-build"),
            "CACHESAGE_VERILATOR_VERSION": _version(["verilator", "--version"], "unknown"),
        }
    )
    test = subprocess.run(
        [sys.executable, "-m", "pytest", "-sv", "integration/nutshell/test_rtl_regression.py"],
        cwd=ROOT,
        env=env,
        check=False,
    )
    if test.returncode != 0 or not output.exists():
        return test.returncode or 1

    evidence = json.loads(output.read_text(encoding="utf-8"))
    waveform = artifact_dir / "nutshell-cache-regression.fst"
    coverage_data = artifact_dir / "coverage.dat"
    evidence["artifacts"]["waveform"] = {
        "path": _relative(waveform),
        "bytes": waveform.stat().st_size if waveform.exists() else 0,
        "committed": False,
    }
    coverage_payload = {
        "status": "not_exported",
        "reason": "未找到 Verilator coverage.dat 或 verilator_coverage。",
    }
    coverage_tool = shutil.which("verilator_coverage")
    if coverage_data.exists() and coverage_tool:
        annotated = artifact_dir / "annotated"
        if annotated.exists():
            shutil.rmtree(annotated)
        result = subprocess.run(
            [coverage_tool, "--annotate", str(annotated), str(coverage_data)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode == 0:
            try:
                summary = parse_verilator_coverage_summary(combined)
            except ValueError:
                coverage_payload = {
                    "status": "not_exported",
                    "reason": "verilator_coverage 已运行，但输出中没有可解析的总计。",
                }
            else:
                coverage_payload = {
                    "status": "exported",
                    "tool": _version([coverage_tool, "--version"], "verilator_coverage"),
                    "artifact": _relative(coverage_data),
                    "annotated_sources": _relative(annotated),
                    "summary": summary,
                    "bytes": coverage_data.stat().st_size,
                    "committed": False,
                }
        else:
            coverage_payload = {
                "status": "not_exported",
                "reason": (result.stderr or result.stdout).strip()[-500:],
            }
    evidence["artifacts"]["rtl_code_coverage"] = coverage_payload
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown.write_text(render_rtl_markdown(evidence), encoding="utf-8")
    print(
        f"RTL 功能覆盖率 {evidence['coverage']['covered']}/{evidence['coverage']['total']} "
        f"({evidence['coverage']['percent']:.2f}%)，Scoreboard 失败 "
        f"{len(evidence['scoreboard']['failures'])}。"
    )
    if coverage_payload["status"] == "exported":
        summary = coverage_payload["summary"]
        print(
            f"RTL 代码覆盖率 {summary['covered_points']}/{summary['total_points']} "
            f"({summary['percent']:.2f}%)。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
