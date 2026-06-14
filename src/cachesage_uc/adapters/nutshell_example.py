from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence


REQUIRED_PATHS = ["Makefile", "rtl", "src", "test"]
DEFAULT_MAKE_TARGETS = {
    "gen_dut": "Generate Picker/Toffee software DUT",
    "test": "Run the upstream Toffee test suite",
    "clean": "Remove generated DUT and build artifacts",
}


@dataclass(frozen=True)
class ExampleNutShellLayout:
    root: Path
    present_paths: List[str]
    missing_paths: List[str]
    make_targets: Dict[str, str] = field(default_factory=dict)
    hint: str = ""

    @property
    def ready(self) -> bool:
        return not self.missing_paths

    def to_dict(self) -> Dict[str, object]:
        return {
            "root": str(self.root),
            "ready": self.ready,
            "present_paths": list(self.present_paths),
            "missing_paths": list(self.missing_paths),
            "make_targets": dict(self.make_targets),
            "hint": self.hint,
        }


def inspect_example_tree(root: Path, required_paths: Sequence[str] = REQUIRED_PATHS) -> ExampleNutShellLayout:
    root = Path(root)
    present = [path for path in required_paths if (root / path).exists()]
    missing = [path for path in required_paths if path not in present]
    targets = _discover_make_targets(root / "Makefile") if "Makefile" in present else {}
    hint = "" if not missing else (
        "Run scripts/fetch_upstream_example.py --lock upstream.lock.json "
        "--dest third_party/Example-NutShellCache before launching the Picker/Toffee smoke flow."
    )
    return ExampleNutShellLayout(
        root=root,
        present_paths=present,
        missing_paths=missing,
        make_targets=targets,
        hint=hint,
    )


def _discover_make_targets(makefile: Path) -> Dict[str, str]:
    targets = dict(DEFAULT_MAKE_TARGETS)
    if not makefile.exists():
        return targets

    try:
        for line in makefile.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            name = stripped.split(":", 1)[0]
            if name and " " not in name and "=" not in name and not name.startswith(".") and name not in targets:
                targets[name] = "Upstream Makefile target"
    except OSError:
        return targets
    return targets
