from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cachesage_uc.evidence import build_default_bundle, render_markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the CacheSage-UC report.")
    parser.add_argument("--output", required=True, help="Markdown report path.")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown_report(build_default_bundle()), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
