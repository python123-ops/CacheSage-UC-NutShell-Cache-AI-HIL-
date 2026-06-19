from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    node = shutil.which("node")
    if node is None:
        print("未找到 Node.js，无法运行可编辑 PPT 构建脚本。", file=sys.stderr)
        return 2
    result = subprocess.run(
        [node, str(ROOT / "scripts" / "build_defense_ppt.mjs")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
