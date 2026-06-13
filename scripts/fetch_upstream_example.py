from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch the pinned Example-NutShellCache workspace.")
    parser.add_argument("--lock", default="upstream.lock.json", help="Path to upstream.lock.json.")
    parser.add_argument("--dest", default="third_party/Example-NutShellCache", help="Destination directory.")
    parser.add_argument("--dry-run", action="store_true", help="Print clone/checkout steps without touching disk.")
    parser.add_argument("--force", action="store_true", help="Replace an existing destination directory.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    lock_path = Path(args.lock)
    dest = Path(args.dest)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    commands = [
        f"git clone --filter=blob:none {lock['remote']} {dest}",
        f"git -C {dest} checkout {lock['commit']}",
    ]
    if args.dry_run:
        print(json.dumps(_summary(lock, dest, commands, dry_run=True), ensure_ascii=False, indent=2))
        return 0

    if dest.exists():
        if not args.force:
            print(
                f"{dest} already exists; pass --force to replace it or choose another --dest.",
                file=sys.stderr,
            )
            return 2
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--filter=blob:none", lock["remote"], str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", lock["commit"]], check=True)

    missing = [path for path in lock["required_paths"] if not (dest / path).exists()]
    summary = _summary(lock, dest, commands, dry_run=False)
    summary["missing_paths"] = missing
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not missing else 3


def _summary(lock: Dict[str, object], dest: Path, commands: List[str], dry_run: bool) -> Dict[str, object]:
    return {
        "dry_run": dry_run,
        "name": lock["name"],
        "repo": lock["repo"],
        "remote": lock["remote"],
        "commit": lock["commit"],
        "dest": str(dest),
        "required_paths": list(lock["required_paths"]),
        "commands": commands,
    }


if __name__ == "__main__":
    raise SystemExit(main())
