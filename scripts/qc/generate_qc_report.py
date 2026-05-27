#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    report = root / "examples" / "reports" / "dummy_qc_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Dummy QC Report\n\n"
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}\n"
        "- Status: dry-run scaffold\n"
        "- Audio analyzed: none\n"
        "- Decision: local trusted-machine test required\n",
        encoding="utf-8",
    )
    print(f"[ok] Wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

