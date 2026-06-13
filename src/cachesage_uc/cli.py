from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

from .evidence import build_default_bundle, render_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cachesage-uc")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("plan", help="Print the verification plan as JSON.")

    report = subcommands.add_parser("report", help="Write the initial markdown report.")
    report.add_argument("--output", required=True, help="Path to the markdown report.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    bundle = build_default_bundle()

    if args.command == "plan":
        print(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "report":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown_report(bundle), encoding="utf-8")
        print(f"wrote {output}")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
