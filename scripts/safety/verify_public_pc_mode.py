#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def git_tracked_local_only(root: Path) -> list[str]:
    try:
        result = subprocess.run(["git", "ls-files", "local_only"], cwd=root, check=False, capture_output=True, text=True)
    except OSError:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    local_machine = os.environ.get("LOCAL_PRODUCTION_MACHINE") == "1"
    execute_install = os.environ.get("EXECUTE_INSTALL") == "1"
    if execute_install and not local_machine:
        print("[fail] EXECUTE_INSTALL=1 requires LOCAL_PRODUCTION_MACHINE=1.")
        return 1
    tracked = git_tracked_local_only(root)
    if tracked:
        print("[fail] local_only content must not be tracked:")
        for item in tracked:
            print(f"- {item}")
        return 1
    print("[ok] Public PC guardrails active. Real install requires LOCAL_PRODUCTION_MACHINE=1, EXECUTE_INSTALL=1, and explicit --execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

