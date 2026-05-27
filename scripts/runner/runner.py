#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str]) -> int:
    print("[run]", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def require_real_execution(args: argparse.Namespace) -> bool:
    if args.execute and os.environ.get("LOCAL_PRODUCTION_MACHINE") == "1" and os.environ.get("EXECUTE_INSTALL") == "1":
        return True
    print("[refuse] Real execution requires --execute, LOCAL_PRODUCTION_MACHINE=1, and EXECUTE_INSTALL=1.")
    return False


def safety_check() -> int:
    checks = [
        ["python", "scripts/safety/verify_no_audio_files.py"],
        ["python", "scripts/safety/verify_no_video_files.py"],
        ["python", "scripts/safety/verify_no_installers.py"],
        ["python", "scripts/safety/verify_no_secrets.py"],
        ["python", "scripts/safety/verify_public_pc_mode.py"],
        ["python", "scripts/safety/verify_manifest_integrity.py"],
    ]
    codes = [run(cmd) for cmd in checks]
    return 0 if all(code == 0 for code in codes) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified v0.2 harness runner.")
    parser.add_argument("--mode", required=True, choices=[
        "safety-check",
        "fixture-test",
        "manifest-check",
        "local-install-dry-run",
        "plugin-scan-dry-run",
        "qc-template",
    ])
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.mode == "safety-check":
        return safety_check()
    if args.mode == "manifest-check":
        return run(["python", "scripts/safety/verify_manifest_integrity.py"])
    if args.mode == "fixture-test":
        if not require_real_execution(args):
            print("[dry-run] Fixture generation skipped on public PC.")
            return 0
        return max(
            run(["python", "scripts/test_fixtures/generate_dummy_vocal_noise.py", "--execute"]),
            run(["python", "scripts/test_fixtures/generate_dummy_mix.py", "--execute"]),
        )
    if args.mode == "local-install-dry-run":
        return run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/local_install/plugins/install_free_plugins_windows.ps1"])
    if args.mode == "plugin-scan-dry-run":
        return run(["python", "scripts/local_install/plugins/verify_reaper_plugin_scan.py"])
    if args.mode == "qc-template":
        return max(
            run(["python", "scripts/qc/score_candidates.py"]),
            run(["python", "scripts/qc/generate_final_decision_report.py"]),
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())

