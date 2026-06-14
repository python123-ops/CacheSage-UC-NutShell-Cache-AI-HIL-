from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
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
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    upstream = ROOT / args.upstream
    output = ROOT / args.output
    markdown = ROOT / args.markdown
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)

    layout = inspect_example_tree(upstream)
    if not layout.ready:
        payload = {
            "status": "missing_upstream",
            "layout": _public_layout(layout),
            "next_command": (
                "python scripts/fetch_upstream_example.py --lock upstream.lock.json "
                "--dest third_party/Example-NutShellCache"
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
            "next_command": "Install Picker, Toffee, Toffee-Test, and make; then rerun scripts/run_nutshell_smoke.py.",
            "note": "The Python harness completed; RTL smoke is waiting on local integration dependencies.",
        }
        _write_outputs(output, markdown, payload)
        print(payload["next_command"], file=sys.stderr)
        return 2

    make_results = {
        "gen_dut": _run_make(upstream, "gen_dut"),
        "test": _run_make(upstream, "test"),
    }
    rtl_status = "rtl_smoke_complete" if all(item["returncode"] == 0 for item in make_results.values()) else "rtl_smoke_failed"
    payload = {
        "status": rtl_status,
        "layout": _public_layout(layout),
        "python_harness": result.to_dict(),
        "toffee_cases_preview": to_toffee_cases(transactions[:8]),
        "make_results": make_results,
        "rtl_toffee_measured_coverage": None,
        "note": "RTL coverage remains separate from the Python harness result until the upstream test exports measured coverage.",
    }
    _write_outputs(output, markdown, payload)
    print(f"wrote {output}")
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
        "# CacheSage-UC NutShell Smoke",
        "",
        f"- Status: `{payload['status']}`",
    ]
    layout = payload.get("layout", {})
    if layout:
        lines.append(f"- Upstream root: `{layout.get('root')}`")
        lines.append(f"- Missing paths: {', '.join(layout.get('missing_paths', [])) or 'none'}")
    if "python_harness" in payload:
        harness = payload["python_harness"]
        lines.append(
            f"- Python harness: {'PASS' if harness['passed'] else 'FAIL'}, "
            f"{harness['coverage']['covered']}/{harness['coverage']['total']} coverpoints"
        )
    if "missing_dependencies" in payload:
        lines.append(f"- Missing dependencies: {', '.join(payload['missing_dependencies'])}")
    if "make_results" in payload:
        for target, result in payload["make_results"].items():
            lines.append(f"- `make {target}`: exit {result['returncode']}")
    if "next_command" in payload:
        lines.append(f"- Next command: `{payload['next_command']}`")
    if "note" in payload:
        lines.append(f"- Note: {payload['note']}")
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
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


if __name__ == "__main__":
    raise SystemExit(main())
