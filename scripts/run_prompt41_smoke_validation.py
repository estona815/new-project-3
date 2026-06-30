#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Prompt41 synthetic/mock AutoMix smoke validation.")
    parser.add_argument("--generate-fixtures", action="store_true")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--mock-render", action="store_true")
    parser.add_argument("--real-render", action="store_true")
    parser.add_argument("--skip-reaper", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cmd = [
        sys.executable,
        str(ROOT / "tests/automix_validation/run_prompt41_validation.py"),
        "--output-dir",
        str(args.output_dir),
    ]
    if not (args.generate_fixtures or args.run_tests):
        cmd.extend(["--generate-fixtures", "--run-tests", "--mock-render"])
    else:
        if args.generate_fixtures:
            cmd.append("--generate-fixtures")
        if args.run_tests:
            cmd.append("--run-tests")
    if args.mock_render:
        cmd.append("--mock-render")
    if args.real_render:
        cmd.append("--real-render")
    if args.skip_reaper:
        cmd.append("--skip-reaper")
    if args.verbose:
        cmd.append("--verbose")
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
