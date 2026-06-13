from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional


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
            "layout": layout.to_dict(),
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
    payload = {
        "status": "python_bridge_smoke_complete",
        "layout": layout.to_dict(),
        "python_harness": result.to_dict(),
        "toffee_cases_preview": to_toffee_cases(transactions[:8]),
        "rtl_toffee_measured_coverage": None,
        "note": "This smoke step validates the CacheSage adapter boundary; RTL coverage is populated after Picker/Toffee dependencies are installed.",
    }
    _write_outputs(output, markdown, payload)
    print(f"wrote {output}")
    return 0 if result.passed else 1


def _write_outputs(output: Path, markdown: Path, payload: dict) -> None:
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown.write_text(_render_markdown(payload), encoding="utf-8")


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
    if "next_command" in payload:
        lines.append(f"- Next command: `{payload['next_command']}`")
    if "note" in payload:
        lines.append(f"- Note: {payload['note']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
