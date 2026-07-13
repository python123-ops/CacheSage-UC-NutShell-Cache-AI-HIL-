from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Sequence


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports" / "rtl-functional-coverage.json"


def run(command: Sequence[str], cwd: Path = ROOT, env=None) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")


def load_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def check_evidence(evidence: dict) -> None:
    errors: List[str] = []
    coverage = evidence.get("coverage", {})
    scoreboard = evidence.get("scoreboard", {})
    backpressure = evidence.get("backpressure", {})
    coverpoints = {item.get("id"): item for item in evidence.get("coverpoints", [])}
    if evidence.get("schema_version") != 2:
        errors.append("RTL evidence schema_version must be 2")
    if coverage.get("covered") != coverage.get("total") or coverage.get("total") != 36:
        errors.append("complete evidence requires real DUT coverage 36/36")
    if evidence.get("status") != "rtl_functional_coverage_complete":
        errors.append("evidence status is not complete")
    if scoreboard.get("failures"):
        errors.append("Scoreboard contains failures")
    for field in ("input_wait_cycles", "response_wait_cycles"):
        if int(backpressure.get(field, 0)) <= 0:
            errors.append(f"backpressure.{field} must be non-zero")
    for field in ("request_payload_stable", "response_payload_stable", "ordered_responses"):
        if backpressure.get(field) is not True:
            errors.append(f"backpressure.{field} must be true")
    for identifier in ("rtl_input_backpressure", "rtl_response_backpressure"):
        point = coverpoints.get(identifier, {})
        if not point.get("covered") or not point.get("sources"):
            errors.append(f"{identifier} lacks real signal source evidence")
    if errors:
        raise RuntimeError("evidence consistency check failed:\n- " + "\n- ".join(errors))


def check_repository_materials(evidence: dict) -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        raise RuntimeError("root LICENSE is not Apache-2.0")
    required = [
        ROOT / "README.md",
        ROOT / "docs" / "scoring-evidence.md",
        ROOT / "docs" / "ucagent-collaboration.md",
        ROOT / "docs" / "picker-toffee-flow.md",
        ROOT / "reports" / "CacheSage-UC-verification-report.md",
        ROOT / "reports" / "CacheSage-UC-defense-demo.pptx",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError("required public materials missing: " + ", ".join(missing))
    current_metrics = [
        f"{evidence['coverage']['covered']}/{evidence['coverage']['total']}",
        str(evidence["run"]["transactions"]),
        str(evidence["scoreboard"]["comparisons"]),
    ]
    metric_materials = [required[index] for index in (0, 1, 2, 3, 4)]
    for path in metric_materials:
        text = path.read_text(encoding="utf-8")
        for value in current_metrics:
            if value not in text:
                raise RuntimeError(
                    f"{path.relative_to(ROOT).as_posix()} lacks current evidence value: {value}"
                )
    link_materials = [required[index] for index in (0, 1, 4)]
    expected_links = [
        "https://github.com/python123-ops/CacheSage-UC-NutShell-Cache-AI-HIL-",
        "https://gitlink.org.cn/python123/cachesage-uc",
    ]
    for path in link_materials:
        text = path.read_text(encoding="utf-8")
        for value in expected_links:
            if value not in text:
                raise RuntimeError(
                    f"{path.relative_to(ROOT).as_posix()} lacks repository link: {value}"
                )
    with zipfile.ZipFile(required[-1]) as archive:
        slides = [
            name for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
    if len(slides) != 12:
        raise RuntimeError(f"defense deck must contain 12 slides, found {len(slides)}")


def portable() -> None:
    evidence = load_evidence()
    check_evidence(evidence)
    check_repository_materials(evidence)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts", "integration"])
    run([sys.executable, "-m", "cachesage_uc.cli", "plan"])
    with tempfile.TemporaryDirectory() as directory:
        run([
            sys.executable, "-m", "cachesage_uc.cli", "run", "--seed", "11", "--count", "32",
            "--output", str(Path(directory) / "acceptance-run.json"),
        ])
    print("portable acceptance: PASS")


def linux_full(upstream: Path) -> None:
    run(["make", "gen_dut"], cwd=upstream)
    run([
        sys.executable,
        "scripts/run_rtl_regression.py",
        "--upstream",
        str(upstream),
    ])
    run([sys.executable, "scripts/build_verification_pdf.py"])


def full(upstream: Path) -> None:
    if os.name != "nt":
        linux_full(upstream)
        portable()
        return
    distro = os.environ.get("CACHESAGE_WSL_DISTRO", "Ubuntu-24.04")
    python = os.environ.get("CACHESAGE_WSL_PYTHON", "/opt/cachesage-uc-smoke-venv/bin/python")

    def wsl_path(path: Path) -> str:
        resolved = path.resolve()
        drive = resolved.drive.rstrip(":").lower()
        tail = resolved.as_posix().split(":", 1)[1]
        return f"/mnt/{drive}{tail}"

    root_linux = wsl_path(ROOT)
    upstream_linux = wsl_path(upstream)
    command = (
        f"set -e; cd '{upstream_linux}'; make gen_dut; "
        f"cd '{root_linux}'; '{python}' scripts/run_rtl_regression.py --upstream '{upstream_linux}'"
    )
    run(["wsl.exe", "-d", distro, "--exec", "bash", "-c", command])
    run([sys.executable, "scripts/build_verification_pdf.py"])
    portable()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify CacheSage-UC competition acceptance evidence.")
    parser.add_argument("--mode", choices=("portable", "full"), required=True)
    parser.add_argument("--upstream", default="third_party/Example-NutShellCache")
    args = parser.parse_args(argv)
    try:
        if args.mode == "portable":
            portable()
        else:
            full((ROOT / args.upstream).resolve())
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"acceptance failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
